import hashlib
import json
import os
import platform
import subprocess
import time
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_LOCK_TIMEOUT = 30


class TokenStore:
	def __init__(self, auth_dir: Path):
		self._auth_dir = auth_dir
		self._auth_dir.mkdir(parents=True, exist_ok=True)
		self._session_path = auth_dir / "session.enc"
		self._salt_path = auth_dir / "salt"
		self._lock_path = auth_dir / "refresh.lock"

	def _get_machine_id(self) -> str:
		system = platform.system()
		if system == "Darwin":
			result = subprocess.run(
				["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
				capture_output=True, text=True,
			)
			for line in result.stdout.splitlines():
				if "IOPlatformUUID" in line:
					return line.split('"')[-2]
		elif system == "Linux":
			machine_id = Path("/etc/machine-id")
			if machine_id.exists():
				return machine_id.read_text().strip()
		elif system == "Windows":
			result = subprocess.run(
				["reg", "query", r"HKLM\SOFTWARE\Microsoft\Cryptography", "/v", "MachineGuid"],
				capture_output=True, text=True,
			)
			for line in result.stdout.splitlines():
				if "MachineGuid" in line:
					return line.split()[-1]
		return "boss-agent-cli-fallback-id"

	def _get_salt(self) -> bytes:
		if self._salt_path.exists():
			return self._salt_path.read_bytes()
		salt = os.urandom(16)
		self._salt_path.write_bytes(salt)
		return salt

	def _derive_key(self) -> bytes:
		salt = self._get_salt()
		machine_id = self._get_machine_id()
		kdf = PBKDF2HMAC(
			algorithm=hashes.SHA256(),
			length=32,
			salt=salt,
			iterations=480000,
		)
		key = kdf.derive(machine_id.encode())
		return urlsafe_b64encode(key)

	def save(self, token_data: dict) -> None:
		fernet = Fernet(self._derive_key())
		plaintext = json.dumps(token_data, ensure_ascii=False).encode()
		encrypted = fernet.encrypt(plaintext)
		self._session_path.write_bytes(encrypted)

	def load(self) -> dict | None:
		if not self._session_path.exists():
			return None
		fernet = Fernet(self._derive_key())
		encrypted = self._session_path.read_bytes()
		plaintext = fernet.decrypt(encrypted)
		return json.loads(plaintext)

	@contextmanager
	def refresh_lock(self):
		deadline = time.time() + _LOCK_TIMEOUT
		while self._lock_path.exists():
			if time.time() > deadline:
				self._lock_path.unlink(missing_ok=True)
				break
			time.sleep(0.5)
		self._lock_path.touch()
		try:
			yield
		finally:
			self._lock_path.unlink(missing_ok=True)

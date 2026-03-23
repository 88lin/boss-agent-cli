BASE_URL = "https://www.zhipin.com"

# ── Web page URLs (for dynamic Referer) ──────────────────────────────
WEB_GEEK_BASE = f"{BASE_URL}/web/geek"
WEB_GEEK_JOB_URL = f"{WEB_GEEK_BASE}/job"
WEB_GEEK_RECOMMEND_URL = f"{WEB_GEEK_BASE}/recommend"
WEB_GEEK_CHAT_URL = f"{WEB_GEEK_BASE}/chat"
WEB_GEEK_RESUME_URL = f"{WEB_GEEK_BASE}/resume"

# ── API endpoints ────────────────────────────────────────────────────
SEARCH_URL = f"{BASE_URL}/wapi/zpgeek/search/joblist.json"
RECOMMEND_URL = f"{BASE_URL}/wapi/zpgeek/pc/recommend/job/list.json"
DETAIL_URL = f"{BASE_URL}/wapi/zpgeek/job/detail.json"
GREET_URL = f"{BASE_URL}/wapi/zpgeek/friend/add.json"
JOB_CARD_URL = f"{BASE_URL}/wapi/zpgeek/job/card.json"
USER_INFO_URL = f"{BASE_URL}/wapi/zpuser/wap/getUserInfo.json"
RESUME_BASEINFO_URL = f"{BASE_URL}/wapi/zpgeek/resume/baseinfo/query.json"
RESUME_EXPECT_URL = f"{BASE_URL}/wapi/zpgeek/resume/expect/query.json"
DELIVER_LIST_URL = f"{BASE_URL}/wapi/zprelation/resume/geekDeliverList"
FRIEND_LIST_URL = f"{BASE_URL}/wapi/zprelation/friend/getGeekFriendList.json"
INTERVIEW_DATA_URL = f"{BASE_URL}/wapi/zpinterview/geek/interview/data.json"
JOB_HISTORY_URL = f"{BASE_URL}/wapi/zpgeek/history/joblist.json"

# ── API response codes ──────────────────────────────────────────────
CODE_SUCCESS = 0            # 请求成功
CODE_STOKEN_EXPIRED = 37    # stoken 过期，需刷新后重试
CODE_RATE_LIMITED = 9       # 请求频率过高，需冷却后重试

# ── Browser-like headers ─────────────────────────────────────────────
DEFAULT_HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
		"AppleWebKit/537.36 (KHTML, like Gecko) "
		"Chrome/145.0.0.0 Safari/537.36"
	),
	"sec-ch-ua": '"Chromium";v="145", "Not(A:Brand";v="99", "Google Chrome";v="145"',
	"sec-ch-ua-mobile": "?0",
	"sec-ch-ua-platform": '"macOS"',
	"Sec-Fetch-Dest": "empty",
	"Sec-Fetch-Mode": "cors",
	"Sec-Fetch-Site": "same-origin",
	"Accept": "application/json, text/plain, */*",
	"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
	"DNT": "1",
	"Origin": BASE_URL,
	"Referer": f"{BASE_URL}/",
}

# ── Endpoint → Referer mapping ───────────────────────────────────────
REFERER_MAP = {
	SEARCH_URL: WEB_GEEK_JOB_URL,
	JOB_CARD_URL: WEB_GEEK_JOB_URL,
	DETAIL_URL: WEB_GEEK_JOB_URL,
	GREET_URL: WEB_GEEK_CHAT_URL,
	RECOMMEND_URL: WEB_GEEK_RECOMMEND_URL,
	USER_INFO_URL: f"{BASE_URL}/",
	RESUME_BASEINFO_URL: WEB_GEEK_RESUME_URL,
	RESUME_EXPECT_URL: WEB_GEEK_RESUME_URL,
	DELIVER_LIST_URL: WEB_GEEK_CHAT_URL,
	FRIEND_LIST_URL: WEB_GEEK_CHAT_URL,
	JOB_HISTORY_URL: WEB_GEEK_JOB_URL,
}

CITY_CODES = {
	"北京": "101010100", "上海": "101020100", "广州": "101280100",
	"深圳": "101280600", "杭州": "101210100", "成都": "101270100",
	"南京": "101190100", "武汉": "101200100", "西安": "101110100",
	"苏州": "101190400", "长沙": "101250100", "郑州": "101180100",
	"重庆": "101040100", "天津": "101030100", "合肥": "101220100",
	"厦门": "101230200", "济南": "101120100", "青岛": "101120200",
	"大连": "101070200", "宁波": "101210400", "福州": "101230100",
	"东莞": "101281600", "珠海": "101280700", "佛山": "101280800",
	"昆明": "101290100", "贵阳": "101260100", "太原": "101100100",
	"南昌": "101240100", "南宁": "101300100", "石家庄": "101090100",
	"哈尔滨": "101050100", "长春": "101060100", "沈阳": "101070100",
	"海口": "101310100", "兰州": "101160100", "乌鲁木齐": "101130100",
	"无锡": "101190200", "常州": "101191100", "温州": "101210700",
	"惠州": "101280300",
}

SALARY_CODES = {
	"3K以下": "401", "3-5K": "402", "5-10K": "403",
	"10-15K": "404", "10-20K": "405", "20-50K": "406", "50K以上": "407",
}

EXPERIENCE_CODES = {
	"应届": "108", "1年以内": "101", "1-3年": "103",
	"3-5年": "104", "5-10年": "105", "10年以上": "106",
}

EDUCATION_CODES = {
	"大专": "202", "本科": "203", "硕士": "204", "博士": "205",
}

SCALE_CODES = {
	"0-20人": "301", "20-99人": "302", "100-499人": "303",
	"500-999人": "304", "1000-9999人": "305", "10000人以上": "306",
}

INDUSTRY_CODES: dict[str, str] = {
	"不限": "0",
	"互联网": "100020",
	"电子商务": "100021",
	"游戏": "100024",
	"软件/信息服务": "100032",
	"人工智能": "100901",
	"大数据": "100902",
	"云计算": "100903",
	"区块链": "100904",
	"物联网": "100905",
	"金融": "100101",
	"银行": "100102",
	"保险": "100103",
	"证券/基金": "100104",
	"教育培训": "100200",
	"医疗健康": "100300",
	"房地产": "100400",
	"汽车": "100500",
	"物流/运输": "100600",
	"广告/传媒": "100700",
	"消费品": "100800",
	"制造业": "101000",
	"能源/环保": "101100",
	"政府/非营利": "101200",
	"农业": "101300",
}

STAGE_CODES: dict[str, str] = {
	"不限": "0",
	"未融资": "801",
	"天使轮": "802",
	"A轮": "803",
	"B轮": "804",
	"C轮": "805",
	"D轮及以上": "806",
	"已上市": "807",
	"不需要融资": "808",
}

JOB_TYPE_CODES: dict[str, str] = {
	"全职": "1901",
	"兼职": "1903",
	"实习": "1903",
}

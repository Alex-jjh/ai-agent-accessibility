/**
 * Website configuration for ecological validity audit.
 * 30 sites across 5 categories, 3 pages each (home, search, detail).
 *
 * Patch ↔ axe-core rule mapping (core of the analysis):
 *   P1  img alt removal        → image-alt
 *   P2  aria-label removal     → aria-label, aria-command-name, aria-input-field-name
 *   P3  label for removal      → label, form-field-multiple-labels
 *   P4  lang attr removal      → html-has-lang
 *   P5  heading→div            → empty-heading, heading-order, page-has-heading-one
 *   P6  tabindex removal       → (no direct rule — focus-order-semantics)
 *   P7  landmark→div           → landmark-main-is-top-level, region, landmark-one-main
 *   P8  duplicate IDs          → duplicate-id, duplicate-id-active, duplicate-id-aria
 *   P9  thead→div, th→td       → td-has-header, th-has-data-cells
 *   P10 label for removal      → (same as P3)
 *   P11 link→span (CUSTOM)     → no axe rule — custom div-as-link detection
 *   P12 Shadow DOM injection   → (no axe rule — structural check only)
 */

export interface SitePage {
  label: string;
  url: string;
}

export interface LoginConfig {
  /** URL to POST login form to */
  loginUrl: string;
  /** Form fields to submit */
  formData: Record<string, string>;
  /** CSS selector to verify login succeeded (e.g. element visible after login) */
  successSelector?: string;
}

export interface SiteConfig {
  name: string;
  category: 'ecommerce' | 'china' | 'saas' | 'media' | 'government' | 'webarena';
  pages: SitePage[];
  /** If true, site is only reachable from EC2 private network (10.0.1.x) */
  requiresInternalNetwork?: boolean;
  /** Login config — browser will perform form login before scanning pages */
  login?: LoginConfig;
}

/** axe-core rule IDs that map to each low-variant patch */
export const PATCH_AXE_RULES: Record<string, string[]> = {
  'P1: img alt':        ['image-alt'],
  'P2: aria-label':     ['aria-label', 'aria-command-name', 'aria-input-field-name'],
  'P3: label for':      ['label', 'form-field-multiple-labels'],
  'P4: lang attr':      ['html-has-lang'],
  'P5: heading→div':    ['empty-heading', 'heading-order', 'page-has-heading-one'],
  'P6: tabindex':       [],  // no direct axe rule
  'P7: landmark→div':   ['landmark-main-is-top-level', 'region', 'landmark-one-main'],
  'P8: duplicate ID':   ['duplicate-id', 'duplicate-id-active', 'duplicate-id-aria'],
  'P9: thead→div':      ['td-has-header', 'th-has-data-cells'],
  'P10: label for':     ['label'],  // same as P3
  'P11: link→span':     [],  // custom detection
  'P12: Shadow DOM':    [],  // structural check
};

export const SITES: SiteConfig[] = [
  // ── Global E-commerce (8) ──
  {
    name: 'amazon',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.amazon.com/' },
      { label: 'search', url: 'https://www.amazon.com/s?k=wireless+earbuds' },
      { label: 'detail', url: 'https://www.amazon.com/dp/B09JQL3NWT' },
    ],
  },
  {
    name: 'ebay',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.ebay.com/' },
      { label: 'search', url: 'https://www.ebay.com/sch/i.html?_nkw=laptop' },
      { label: 'detail', url: 'https://www.ebay.com/itm/123456789' },
    ],
  },
  {
    name: 'walmart',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.walmart.com/' },
      { label: 'search', url: 'https://www.walmart.com/search?q=headphones' },
      { label: 'detail', url: 'https://www.walmart.com/ip/123456789' },
    ],
  },
  {
    name: 'target',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.target.com/' },
      { label: 'search', url: 'https://www.target.com/s?searchTerm=keyboard' },
      { label: 'detail', url: 'https://www.target.com/p/-/A-12345678' },
    ],
  },
  {
    name: 'etsy',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.etsy.com/' },
      { label: 'search', url: 'https://www.etsy.com/search?q=handmade+jewelry' },
      { label: 'detail', url: 'https://www.etsy.com/listing/1234567890' },
    ],
  },
  {
    name: 'bestbuy',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.bestbuy.com/' },
      { label: 'search', url: 'https://www.bestbuy.com/site/searchpage.jsp?st=monitor' },
      { label: 'detail', url: 'https://www.bestbuy.com/site/6534424.p' },
    ],
  },
  {
    name: 'aliexpress',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.aliexpress.com/' },
      { label: 'search', url: 'https://www.aliexpress.com/wholesale?SearchText=usb+cable' },
      { label: 'detail', url: 'https://www.aliexpress.com/item/1005001234567890.html' },
    ],
  },
  {
    name: 'shein',
    category: 'ecommerce',
    pages: [
      { label: 'home', url: 'https://www.shein.com/' },
      { label: 'search', url: 'https://www.shein.com/pdsearch/dress/' },
      { label: 'detail', url: 'https://www.shein.com/product-p-12345678.html' },
    ],
  },

  // ── China Platforms (6) ──
  {
    name: 'jd',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://www.jd.com/' },
      { label: 'search', url: 'https://search.jd.com/Search?keyword=手机' },
      { label: 'detail', url: 'https://item.jd.com/100012043978.html' },
    ],
  },
  {
    name: 'taobao',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://www.taobao.com/' },
      { label: 'search', url: 'https://s.taobao.com/search?q=耳机' },
      { label: 'detail', url: 'https://item.taobao.com/item.htm?id=123456789' },
    ],
  },
  {
    name: 'bilibili',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://www.bilibili.com/' },
      { label: 'search', url: 'https://search.bilibili.com/all?keyword=programming' },
      { label: 'detail', url: 'https://www.bilibili.com/video/BV1xx411c7mD' },
    ],
  },
  {
    name: 'zhihu',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://www.zhihu.com/' },
      { label: 'search', url: 'https://www.zhihu.com/search?type=content&q=accessibility' },
      { label: 'detail', url: 'https://www.zhihu.com/question/19550227' },
    ],
  },
  {
    name: 'douyin',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://www.douyin.com/' },
      { label: 'search', url: 'https://www.douyin.com/search/coding' },
      { label: 'detail', url: 'https://www.douyin.com/video/7123456789012345678' },
    ],
  },
  {
    name: 'weibo',
    category: 'china',
    pages: [
      { label: 'home', url: 'https://weibo.com/' },
      { label: 'search', url: 'https://s.weibo.com/weibo?q=AI' },
      { label: 'detail', url: 'https://weibo.com/1234567890/abcdefg' },
    ],
  },

  // ── SaaS / Tools (6) ──
  {
    name: 'github',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://github.com/' },
      { label: 'search', url: 'https://github.com/search?q=playwright&type=repositories' },
      { label: 'detail', url: 'https://github.com/microsoft/playwright' },
    ],
  },
  {
    name: 'gitlab',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://gitlab.com/' },
      { label: 'search', url: 'https://gitlab.com/search?search=accessibility' },
      { label: 'detail', url: 'https://gitlab.com/gitlab-org/gitlab' },
    ],
  },
  {
    name: 'notion',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://www.notion.so/' },
      { label: 'search', url: 'https://www.notion.so/product' },
      { label: 'detail', url: 'https://www.notion.so/templates' },
    ],
  },
  {
    name: 'trello',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://trello.com/' },
      { label: 'search', url: 'https://trello.com/platforms' },
      { label: 'detail', url: 'https://trello.com/guide' },
    ],
  },
  {
    name: 'slack',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://slack.com/' },
      { label: 'search', url: 'https://slack.com/features' },
      { label: 'detail', url: 'https://slack.com/pricing' },
    ],
  },
  {
    name: 'salesforce',
    category: 'saas',
    pages: [
      { label: 'home', url: 'https://www.salesforce.com/' },
      { label: 'search', url: 'https://www.salesforce.com/products/' },
      { label: 'detail', url: 'https://www.salesforce.com/crm/' },
    ],
  },

  // ── Content / Media (5) ──
  {
    name: 'reddit',
    category: 'media',
    pages: [
      { label: 'home', url: 'https://www.reddit.com/' },
      { label: 'search', url: 'https://www.reddit.com/search/?q=accessibility' },
      { label: 'detail', url: 'https://www.reddit.com/r/webdev/' },
    ],
  },
  {
    name: 'medium',
    category: 'media',
    pages: [
      { label: 'home', url: 'https://medium.com/' },
      { label: 'search', url: 'https://medium.com/search?q=web+accessibility' },
      { label: 'detail', url: 'https://medium.com/tag/accessibility' },
    ],
  },
  {
    name: 'nytimes',
    category: 'media',
    pages: [
      { label: 'home', url: 'https://www.nytimes.com/' },
      { label: 'search', url: 'https://www.nytimes.com/search?query=technology' },
      { label: 'detail', url: 'https://www.nytimes.com/section/technology' },
    ],
  },
  {
    name: 'bbc',
    category: 'media',
    pages: [
      { label: 'home', url: 'https://www.bbc.com/' },
      { label: 'search', url: 'https://www.bbc.co.uk/search?q=accessibility' },
      { label: 'detail', url: 'https://www.bbc.com/news/technology' },
    ],
  },
  {
    name: 'wikipedia',
    category: 'media',
    pages: [
      { label: 'home', url: 'https://en.wikipedia.org/' },
      { label: 'search', url: 'https://en.wikipedia.org/w/index.php?search=web+accessibility' },
      { label: 'detail', url: 'https://en.wikipedia.org/wiki/Web_accessibility' },
    ],
  },

  // ── Government / Education (5) ──
  {
    name: 'usa-gov',
    category: 'government',
    pages: [
      { label: 'home', url: 'https://www.usa.gov/' },
      { label: 'search', url: 'https://www.usa.gov/search?query=benefits' },
      { label: 'detail', url: 'https://www.usa.gov/disability-services' },
    ],
  },
  {
    name: 'gov-uk',
    category: 'government',
    pages: [
      { label: 'home', url: 'https://www.gov.uk/' },
      { label: 'search', url: 'https://www.gov.uk/search/all?keywords=accessibility' },
      { label: 'detail', url: 'https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps' },
    ],
  },
  {
    name: 'harvard',
    category: 'government',
    pages: [
      { label: 'home', url: 'https://www.harvard.edu/' },
      { label: 'search', url: 'https://www.harvard.edu/search/?q=computer+science' },
      { label: 'detail', url: 'https://www.harvard.edu/about/' },
    ],
  },
  {
    name: 'mit',
    category: 'government',
    pages: [
      { label: 'home', url: 'https://www.mit.edu/' },
      { label: 'search', url: 'https://search.mit.edu/?q=accessibility' },
      { label: 'detail', url: 'https://www.mit.edu/about/' },
    ],
  },
  {
    name: 'xjtlu',
    category: 'government',
    pages: [
      { label: 'home', url: 'https://www.xjtlu.edu.cn/en' },
      { label: 'search', url: 'https://www.xjtlu.edu.cn/en/search?q=computer+science' },
      { label: 'detail', url: 'https://www.xjtlu.edu.cn/en/about' },
    ],
  },

  // ── WebArena Docker Environments (4) — EC2 internal network only ──
  {
    name: 'webarena-gitlab',
    category: 'webarena',
    requiresInternalNetwork: true,
    pages: [
      { label: 'home', url: 'http://10.0.1.50:8023/explore' },
      { label: 'search', url: 'http://10.0.1.50:8023/search?search=super_awesome_robot' },
      { label: 'detail', url: 'http://10.0.1.50:8023/primer/design' },
      { label: 'contributors', url: 'http://10.0.1.50:8023/primer/design/-/graphs/main' },
    ],
  },
  {
    name: 'webarena-shopping',
    category: 'webarena',
    requiresInternalNetwork: true,
    pages: [
      { label: 'home', url: 'http://10.0.1.50:7770/' },
      { label: 'search', url: 'http://10.0.1.50:7770/catalogsearch/result/?q=shirt' },
      { label: 'detail', url: 'http://10.0.1.50:7770/beautiful-halls-702.html' },
    ],
  },
  {
    name: 'webarena-admin',
    category: 'webarena',
    requiresInternalNetwork: true,
    login: {
      loginUrl: 'http://10.0.1.50:7780/admin/',
      formData: {
        'login[username]': 'admin',
        'login[password]': 'admin1234',
      },
      successSelector: '.admin__menu',
    },
    pages: [
      { label: 'home', url: 'http://10.0.1.50:7780/admin/' },
      { label: 'orders', url: 'http://10.0.1.50:7780/admin/sales/order/' },
      { label: 'invoices', url: 'http://10.0.1.50:7780/admin/sales/invoice/' },
    ],
  },
  {
    name: 'webarena-reddit',
    category: 'webarena',
    requiresInternalNetwork: true,
    pages: [
      { label: 'home', url: 'http://10.0.1.50:9999/' },
      { label: 'forum', url: 'http://10.0.1.50:9999/f/gaming' },
      { label: 'detail', url: 'http://10.0.1.50:9999/f/gaming/1/test-post' },
    ],
  },
];

"""Read the four Integrity WordPress APIs without changing their source data."""

from dataclasses import dataclass, field
from html import escape, unescape
from urllib.parse import unquote, urlsplit, urlunsplit
import re

import requests
from bs4 import BeautifulSoup


CMS = "https://cms-corporate.integrity-asia.com"
SITES = {
    "integrity-indonesia.com": ("Integrity Indonesia", "id"),
    "integrity-malaysia.com": ("Integrity Malaysia", "ms"),
    "integrity-thailand.com": ("Integrity Thailand", "th"),
    "integrity-asia.com": ("Integrity Asia", "asia"),
}
# Only content fields are requested: styling, IDs and layout settings aren't prose.
TEXT_FIELDS = set("""title subtitle heading headingHighlight content description text
    introText label quote authorName authorPosition officeName address email phone
    question answer stageLabel additionalInfoText value step traditional withKnowme
    carouselLabel tableTitle tableColStep tableColTraditional tableColKnowme altText
    sectionTitle sectionSubtitle buttonText ctaText name caption""".split())
IMAGE_FIELDS = set("""image imageUrl sideImage timelineImage sideAccentImage logoImage
    companyLogo sourceUrl""".split())
LINK_FIELDS = {"link", "url", "buttonLink", "ctaLink"}
FIRST_FIELDS = ["sectionTitle", "sectionSubtitle", "heading", "headingHighlight",
                "stageLabel", "title", "subtitle", "introText", "question", "quote",
                "authorName", "authorPosition", "officeName", "address", "phone", "email"]
SKIP_OBJECTS = {"ancestors", "children", "parent", "translations", "seo"}


class ExportError(ValueError):
    """An actionable error that can be displayed to a user."""


@dataclass
class Page:
    url: str
    site: str
    language: str
    title: str
    content: str
    seo: dict
    warnings: list[str] = field(default_factory=list)

    @property
    def metadata(self):
        values = [("Title tag", self.seo.get("title")),
                  ("Meta description", self.seo.get("metaDesc")),
                  ("URL", self.url),
                  ("Keyword utama (focus keyword)", self.seo.get("focuskw"))]
        return [(label, unescape(str(value)) if value and str(value).strip() else "Kosong")
                for label, value in values]


def parse_url(value):
    value = value.strip()
    if not value:
        raise ExportError("Masukkan URL halaman yang ingin diekspor.")
    if "://" not in value:
        value = "https://" + value
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        port = parsed.port
    except ValueError as exc:
        raise ExportError("URL tidak valid. Salin URL lengkap dari browser.") from exc
    if (host not in SITES or parsed.scheme not in {"http", "https"}
            or parsed.username or parsed.password or port not in {None, 80, 443}):
        raise ExportError("Gunakan URL dari Integrity Indonesia, Malaysia, Thailand, atau Asia.")
    path = unquote(parsed.path or "/")
    if any(part in {".", ".."} for part in path.split("/")) or "\\" in path:
        raise ExportError("Path URL tidak valid. Salin ulang URL dari website.")
    name, code = SITES[host]
    prefix = path.strip("/").split("/")[0]
    language = prefix if prefix in {"id", "ms", "th", "en"} else "en"
    if language not in {"en", code}:
        raise ExportError("Bahasa pada URL tidak tersedia untuk website tersebut.")
    url = urlunsplit(("https", "www." + host, parsed.path or "/", "", ""))
    return url, path, name, code, language


class Client:
    def __init__(self, code):
        self.endpoint = f"{CMS}/{code}/graphql"
        self.multilingual = code != "asia"
        self.types = {}

    def query(self, query, variables=None):
        try:
            response = requests.post(self.endpoint, json={"query": query, "variables": variables or {}},
                                     timeout=(8, 45), allow_redirects=False)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ExportError("API belum dapat dihubungi. Coba lagi dalam beberapa saat.") from exc
        if payload.get("errors") or not isinstance(payload.get("data"), dict):
            raise ExportError("API tidak dapat membaca halaman ini. Coba URL lain atau ulangi nanti.")
        return payload["data"]

    @property
    def identity(self):
        language = "languageCode translations { id uri languageCode }" if self.multilingual else ""
        return "__typename id title slug uri " + language

    def locate(self, path, language):
        identity = self.identity
        query = ("query($uri:String!) { nodeByUri(uri:$uri) { __typename "
                 f"... on Post {{ {identity} }} ... on Page {{ {identity} }} }} }}")
        node = self.query(query, {"uri": path})["nodeByUri"]
        if node and node.get("__typename") in {"Page", "Post"}:
            if not self.multilingual or node.get("languageCode") == language:
                return node
            translations = [n for n in node.get("translations") or [] if n.get("languageCode") == language]
            if len(translations) == 1:
                return {**translations[0], "__typename": node["__typename"]}
        slug = path.rstrip("/").rsplit("/", 1)[-1]
        lang_arg = ", language:$language" if self.multilingual else ""
        declaration = ", $language:String" if self.multilingual else ""
        query = (f"query($slug:String!{declaration}) {{ "
                 f"posts(first:3, where:{{name:$slug{lang_arg}}}) {{ nodes {{ {identity} }} }} "
                 f"pages(first:3, where:{{name:$slug{lang_arg}}}) {{ nodes {{ {identity} }} }} }}")
        variables = {"slug": slug}
        if self.multilingual:
            variables["language"] = language
        result = self.query(query, variables)
        # Post permalinks can omit /blog/. Pages must match their hierarchy too.
        matches = []
        for kind in ["posts", "pages"]:
            for item in result[kind]["nodes"]:
                if self.multilingual and item.get("languageCode") != language:
                    continue
                if kind == "pages" and item.get("uri", "").rstrip("/") != path.rstrip("/"):
                    continue
                if kind == "posts" and "/blog/" not in path and item.get("uri", "").rstrip("/") != path.rstrip("/"):
                    continue
                if item.get("slug") == slug:
                    matches.append(item)
        if len(matches) != 1:
            raise ExportError("Halaman dengan URL dan bahasa tersebut tidak ditemukan di API. Periksa URL-nya.")
        return matches[0]

    def load_types(self, names):
        names = sorted(set(names) - self.types.keys())
        if not names:
            return
        # Type names come from the API, but are still checked before query interpolation.
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names):
            raise ExportError("Struktur komponen API tidak valid.")
        fragments = [f't{i}: __type(name:"{name}") {{ fields {{ name type {{ kind name '
                     'ofType { kind name ofType { kind name } } } } }'
                     for i, name in enumerate(names)]
        data = self.query("{" + " ".join(fragments) + "}")
        for i, name in enumerate(names):
            self.types[name] = (data.get(f"t{i}") or {}).get("fields") or []

    def component_selection(self, names):
        # Component fields may contain repeaters and nested text/image objects.
        frontier = set(names)
        for _ in range(4):
            self.load_types(frontier)
            nested = set()
            for name in frontier:
                for item in self.types[name]:
                    kind = unwrap(item["type"])
                    if kind["kind"] == "OBJECT" and item["name"] not in SKIP_OBJECTS:
                        nested.add(kind["name"])
            frontier = nested - self.types.keys()
            if not frontier:
                break

        def select(name, depth=0):
            fields = []
            for item in self.types.get(name, []):
                key, kind = item["name"], unwrap(item["type"])
                if kind["kind"] == "SCALAR" and key in TEXT_FIELDS | IMAGE_FIELDS | LINK_FIELDS:
                    fields.append(key)
                elif kind["kind"] == "OBJECT" and depth < 3 and key not in SKIP_OBJECTS:
                    child = select(kind["name"], depth + 1)
                    if child:
                        fields.append(key + " { " + child + " }")
            return " ".join(fields)

        return {name: select(name) for name in names}

    def read(self, identity):
        kind = identity["__typename"]
        extra = ("integrityPageTitle { pageTitleCustomTitle pageTitleSubtitle pageTitleDescription "
                 "pageTitleCtaText pageTitleCtaLink } customFields { __typename type }") if kind == "Page" else ""
        fields = ("title content uri seo { title metaDesc focuskw } "
                  "featuredImage { node { sourceUrl altText } } " + extra)
        data = self.query(f"query($id:ID!) {{ {kind.lower()}(id:$id) {{ {fields} }} }}", {"id": identity["id"]})
        node = data[kind.lower()]
        if not node:
            raise ExportError("Konten halaman tidak ditemukan di API.")
        components = node.get("customFields") or []
        names = {c["__typename"] for c in components}
        if names:
            selections = self.component_selection(names)
            fragments = " ".join(f"... on {name} {{ {value} }}" for name, value in selections.items() if value)
            custom = self.query("query($id:ID!) { page(id:$id) { customFields { __typename type "
                                + fragments + " } } }", {"id": identity["id"]})
            node["customFields"] = custom["page"]["customFields"]
        return node


def unwrap(value):
    while value.get("ofType"):
        value = value["ofType"]
    return value


def markup(value):
    """Keep actual rich text; escape scalar prose instead of interpreting it as HTML."""
    value = str(value)
    if re.search(r"</?(?:p|div|span|strong|b|em|i|ul|ol|li|h[1-6]|a|br|table)\b", value, re.I):
        return value
    return escape(unescape(value))


def component_html(component):
    parts = []
    keys = sorted(component, key=lambda k: (FIRST_FIELDS.index(k) if k in FIRST_FIELDS else len(FIRST_FIELDS)))
    for key in keys:
        value = component[key]
        if value is None or value == "" or key in {"type", "__typename", "altText"} | LINK_FIELDS:
            continue
        if isinstance(value, list):
            parts.extend(component_html(item) if isinstance(item, dict) else "" for item in value)
        elif isinstance(value, dict):
            parts.append(component_html(value))
        elif key in IMAGE_FIELDS:
            width = ' width="120"' if key in {"logoImage", "companyLogo"} else ""
            parts.append(f'<p><img src="{escape(str(value), quote=True)}" alt="{escape(str(component.get("altText") or ""), quote=True)}"{width}></p>')
        elif key in TEXT_FIELDS:
            tag = "h2" if key in {"sectionTitle", "heading", "tableTitle"} else "h3" if key in {"title", "question"} else "p"
            rendered = markup(value)
            link = next((component.get(k) for k in ["buttonLink", "ctaLink", "link", "url"] if component.get(k)), None)
            if link and key in {"title", "buttonText", "ctaText"}:
                rendered = f'<a href="{escape(str(link), quote=True)}">{rendered}</a>'
            parts.append(rendered if re.search(r"<(?:p|div|ul|ol|table|h[1-6])\b", rendered, re.I) else f"<{tag}>{rendered}</{tag}>")
    return "\n".join(parts)


def fetch_page(url):
    url, path, site, code, language = parse_url(url)
    client = Client(code)
    identity = client.locate(path, language)
    node = client.read(identity)
    header = node.get("integrityPageTitle") or {}
    title = unescape(header.get("pageTitleCustomTitle") or node.get("title") or "")
    content = []
    warnings = []
    for key in ["pageTitleSubtitle", "pageTitleDescription", "pageTitleCtaText"]:
        if header.get(key):
            rendered = markup(header[key])
            if key == "pageTitleCtaText" and header.get("pageTitleCtaLink"):
                rendered = f'<a href="{escape(header["pageTitleCtaLink"], quote=True)}">{rendered}</a>'
            content.append(rendered if re.search(r"<(?:p|div|ul|ol|table)\b", rendered, re.I) else f"<p>{rendered}</p>")
    image = (node.get("featuredImage") or {}).get("node") or {}
    if image.get("sourceUrl") and not BeautifulSoup(node.get("content") or "", "html.parser").find("img"):
        content.append(f'<p><img src="{escape(image["sourceUrl"], quote=True)}" alt="{escape(image.get("altText") or "", quote=True)}"></p>')
    content.append(node.get("content") or "")
    for component in node.get("customFields") or []:
        fragment = component_html(component)
        if not fragment:
            warnings.append("Satu komponen halaman tidak menyediakan konten yang dapat diekspor.")
        content.append(fragment)
    html = "\n".join(content)
    if not BeautifulSoup(html, "html.parser").get_text(strip=True) and not BeautifulSoup(html, "html.parser").find("img"):
        warnings.append("Konten: Kosong. API tidak menyediakan isi halaman ini.")
    if "\ufffd" in title + html:
        warnings.append("Sumber API mengandung karakter rusak (�). Karakter sumber dipertahankan tanpa koreksi otomatis.")
    return Page(url, site, language, title, html, node.get("seo") or {}, list(dict.fromkeys(warnings)))

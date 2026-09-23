import requests
import time
import os
import csv

GRAPHQL_URL = "https://cms-corporate.integrity-asia.com/id/graphql"

PER_PAGE = 50
OUTPUT_FILE = "integrity_articles.csv"

all_posts = []
cursor = None
page = 1


def get_posts(cursor=None):

    if cursor:
        query = f"""
        {{
            posts(
                first: {PER_PAGE}
                after: "{cursor}"
            ) {{
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
                nodes {{
                    id
                    title
                    uri
                    slug
                    date

                    author {{
                        node {{
                            name
                        }}
                    }}

                    categories {{
                        nodes {{
                            name
                            slug
                        }}
                    }}

                    tags {{
                        nodes {{
                            name
                            slug
                        }}
                    }}

                    content
                    excerpt

                    languageCode
                    translationGroupId

                    seo {{
                        title
                        metaDesc
                        focuskw
                        metaKeywords
                        canonical
                    }}
                }}
            }}
        }}
        """
    else:
        query = f"""
        {{
            posts(first: {PER_PAGE}) {{
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
                nodes {{
                    id
                    title
                    uri
                    slug
                    date

                    author {{
                        node {{
                            name
                        }}
                    }}

                    categories {{
                        nodes {{
                            name
                            slug
                        }}
                    }}

                    tags {{
                        nodes {{
                            name
                            slug
                        }}
                    }}

                    content
                    excerpt

                    languageCode
                    translationGroupId

                    seo {{
                        title
                        metaDesc
                        focuskw
                        metaKeywords
                        canonical
                    }}
                }}
            }}
        }}
        """

    for attempt in range(5):

        try:

            print(f"  Koneksi percobaan {attempt + 1}/5...")

            response = requests.post(
                GRAPHQL_URL,
                json={"query": query},
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            if "errors" in data:

                print("\nGraphQL Error:")
                print(data["errors"])
                return None

            return data["data"]["posts"]

        except requests.exceptions.RequestException as e:

            print("  Koneksi gagal.")

            if attempt < 4:

                print("  Menunggu 15 detik...")
                time.sleep(15)

            else:

                print("  Gagal setelah 5 percobaan.")

    return None


while True:

    print("\n" + "=" * 70)
    print(f"MENGAMBIL HALAMAN {page}")
    print("=" * 70)

    result = get_posts(cursor)

    if result is None:

        print("\nProses berhenti karena koneksi gagal.")
        print(f"Artikel yang sudah berhasil diambil: {len(all_posts)}")

        break

    posts = result["nodes"]

    all_posts.extend(posts)

    print(f"Artikel halaman ini : {len(posts)}")
    print(f"Total sementara     : {len(all_posts)}")

    page_info = result["pageInfo"]

    if not page_info["hasNextPage"]:

        print("\nSudah mencapai halaman terakhir.")
        break

    cursor = page_info["endCursor"]

    time.sleep(5)

    page += 1


# ==========================================================
# SIMPAN KE CSV
# ==========================================================

if all_posts:

    print("\nMenyimpan data ke CSV...")

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "ID",
                "Title",
                "URL",
                "Slug",
                "Date",
                "Author",
                "Category",
                "Tags",
                "Content",
                "Excerpt",
                "Language",
                "Translation Group ID",
                "SEO Title",
                "Meta Description",
                "Focus Keyword",
                "Meta Keywords",
                "Canonical"
            ]
        )

        writer.writeheader()

        for post in all_posts:

            author = ""

            if post.get("author") and post["author"].get("node"):
                author = post["author"]["node"].get("name", "")

            categories = ""

            if post.get("categories"):
                categories = ", ".join(
                    category["name"]
                    for category in post["categories"]["nodes"]
                )

            tags = ""

            if post.get("tags"):
                tags = ", ".join(
                    tag["name"]
                    for tag in post["tags"]["nodes"]
                )

            seo = post.get("seo") or {}

            writer.writerow({
                "ID": post.get("id", ""),
                "Title": post.get("title", ""),
                "URL": post.get("uri", ""),
                "Slug": post.get("slug", ""),
                "Date": post.get("date", ""),
                "Author": author,
                "Category": categories,
                "Tags": tags,
                "Content": post.get("content", ""),
                "Excerpt": post.get("excerpt", ""),
                "Language": post.get("languageCode", ""),
                "Translation Group ID": post.get("translationGroupId", ""),
                "SEO Title": seo.get("title", ""),
                "Meta Description": seo.get("metaDesc", ""),
                "Focus Keyword": seo.get("focuskw", ""),
                "Meta Keywords": seo.get("metaKeywords", ""),
                "Canonical": seo.get("canonical", "")
            })

    print("\n" + "=" * 70)
    print("SELESAI")
    print("=" * 70)
    print(f"Total artikel : {len(all_posts)}")
    print(f"File          : {OUTPUT_FILE}")

else:

    print("\nTidak ada data yang berhasil diambil.")
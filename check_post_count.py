import requests
import time

GRAPHQL_URL = "https://cms-corporate.integrity-asia.com/id/graphql"

query = """
{
    post(id: "cG9zdDo0MTAzMQ==") {
        id
        title
        uri
        languageCode
        translationGroupId

        language {
            code
            language_code
            native_name
            translated_name
            url
        }

        translations {
            id
            title
            uri
            languageCode
            translationGroupId

            language {
                code
                language_code
                native_name
                translated_name
                url
            }
        }
    }
}
"""

print("Menghubungkan ke GraphQL...")

for attempt in range(5):

    try:

        print(f"Percobaan {attempt + 1}/5...")

        response = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            print("\nGraphQL Error:")
            print(data["errors"])
            break

        post = data["data"]["post"]

        print("\n" + "=" * 70)
        print("POST UTAMA")
        print("=" * 70)

        print("Title           :", post["title"])
        print("URI             :", post["uri"])
        print("Language Code   :", post["languageCode"])
        print("Translation ID  :", post["translationGroupId"])
        print("Language        :", post["language"])

        print("\n" + "=" * 70)
        print("TRANSLATIONS")
        print("=" * 70)

        translations = post["translations"]

        if not translations:
            print("Tidak ada translation.")

        for translation in translations:

            print("\nTitle           :", translation["title"])
            print("URI             :", translation["uri"])
            print("Language Code   :", translation["languageCode"])
            print("Translation ID  :", translation["translationGroupId"])
            print("Language        :", translation["language"])

        break

    except requests.exceptions.RequestException as e:

        print("Koneksi gagal.")

        if attempt < 4:
            print("Menunggu 15 detik...")
            time.sleep(15)
        else:
            print("Gagal setelah 5 percobaan.")
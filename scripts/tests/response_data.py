"""
Holds dummy data for tests
"""
RESPONSE_GET_ORGANIZATION = {
    'data': [
        {
            'id': 'o:open-edx',
            'type': 'organizations',
            'attributes': {
                'name': 'Open edX',
                'slug': 'open-edx',
                'private': False
            },
            'relationships': {
            }
        }
    ],
}

RESPONSE_GET_PROJECT = {
    "data": {
        "id": "o:open-edx:p:openedx-translations",
        "type": "project",
        "attributes": {
            "slug": "openedx-translations",
            "name": "openedx-translations",
            "type": "file",
        },
        "relationships": {
        },
    }
}

RESPONSE_GET_LANGUAGE = {
    "data": {
        "id": "l:ar",
        "type": "language",
        "attributes": {
            "code": "ar",
            "name": "Arabic",
            "rtl": True,
            "plural_equation": "n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5",
            "plural_rules": {
                "zero": "n is 0",
                "one": "n is 1",
                "two": "n is 2",
                "many": "n mod 100 in 11..99",
                "few": "n mod 100 in 3..10",
                "other": "everything else"
            }
        },
        "links": {
            "self": "https://rest.api.transifex.com/languages/l:ar"
        },
        "relationships": {
        },
    }
}

RESPONSE_GET_LANGUAGES = {
    'data': [
        RESPONSE_GET_LANGUAGE['data'],
    ]
}

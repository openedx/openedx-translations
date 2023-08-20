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
        'projects': {
          'links': {
            'related': 'https://rest.api.transifex.com/projects?filter[organization]=o:open-edx'
          }
        },
      }
    }
  ],
}

RESPONSE_GET_PROJECTS = {
  "data": [
    {
      "id": "o:open-edx:p:openedx-translations",
      "type": "projects",
      "attributes": {
        "slug": "openedx-translations",
        "name": "openedx-translations",
        "type": "file",
      },
      "relationships": {
        "source_language": {
          "links": {
            "related": "https://rest.api.transifex.com/languages/l:en"
          },
          "data": {
            "type": "languages",
            "id": "l:en"
          }
        },
        "languages": {
          "links": {
            "self": "https://rest.api.transifex.com/projects/o:open-edx:p:openedx-translations/relationships/languages",
            "related": "https://rest.api.transifex.com/projects/o:open-edx:p:openedx-translations/languages"
          }
        },
      },
    }
  ],
}

RESPONSE_GET_LANGUAGE = {
  "data": [
    {
      "id": "l:ar",
      "type": "languages",
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
      }
    }
  ]
}

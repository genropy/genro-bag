# OpenApiResolver Demo

Loads an OpenAPI spec and organizes endpoints by tags with ready-to-use UrlResolvers.

```python
>>> from genro_bag import Bag
>>> from genro_bag.resolvers import OpenApiResolver
>>>
>>> bag = Bag()
>>> bag['petstore'] = OpenApiResolver('https://petstore3.swagger.io/api/v3/openapi.json')
>>>
>>> api = bag['petstore']
>>> list(api.keys())
['info', 'externalDocs', 'servers', 'api', 'components']
>>>
>>> api['info']
'This is a sample Pet Store Server based on the OpenAPI 3.0 specification.'
>>>
>>> list(api['api'].keys())
['pet', 'store', 'user']
>>>
>>> list(api['api.pet'].keys())
['updatePet', 'addPet', 'findPetsByStatus', 'findPetsByTags', 'getPetById', 'updatePetWithForm', 'deletePet', 'uploadFile']
>>>
>>> op = api['api.pet.findPetsByStatus']
>>> op['summary']
'Finds Pets by status'
>>>
>>> op['method']
'get'
>>>
>>> op['path']
'/pet/findByStatus'
>>>
>>> # Set query parameters and invoke
>>> op['qs.status'] = 'available'
>>> result = op['value']  # triggers the API call
>>> result['0.name']
'doggie'
>>>
>>> print(api.to_string())
├── info: 'This is a sample Pet Store Server...'
├── externalDocs
│   ├── description: 'Find out more about Swagger'
│   └── url: 'https://swagger.io'
├── servers
│   └── 0
│       └── url: '/api/v3'
├── api
│   ├── pet [name='pet', description='Everything about your Pets']
│   │   ├── updatePet
│   │   │   ├── summary: 'Update an existing pet'
│   │   │   ├── method: 'put'
│   │   │   ├── path: '/pet'
│   │   │   └── ...
│   │   ├── addPet
│   │   │   └── ...
│   │   ├── findPetsByStatus
│   │   │   ├── summary: 'Finds Pets by status'
│   │   │   ├── method: 'get'
│   │   │   ├── path: '/pet/findByStatus'
│   │   │   ├── qs
│   │   │   │   └── status: None
│   │   │   └── value: <UrlResolver>
│   │   └── ...
│   ├── store [name='store', description='Access to Petstore orders']
│   │   └── ...
│   └── user [name='user', description='Operations about user']
│       └── ...
└── components
    ├── schemas
    │   ├── Pet
    │   ├── Category
    │   └── ...
    └── securitySchemes
        └── ...
```

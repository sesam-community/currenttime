# CurrentTime

## This is a repo for connecting to the Unit4 API
This repo lets you [GET], [POST], [PUT] and [DELETE]

For documentation, look here:
https://app-u4-olavstoppen-api.azurewebsites.net/swagger/ui/index.html#/

## Routes:

```/get/<path>```

```/post/<path>```

```/post/<path>/<resource_path>```

The microservice supports the use of since in Sesam. This is implemented in the ```/get/<path>``` route.

## How to:

*Run program in development*

This repo uses the file ```package.json``` and [yarn](https://yarnpkg.com/lang/en/) to run the required commands.

1. Make sure you have installed yarn.
2. Creata a file called ```helpers.json``` and set current_url, current_user and current_password in the following format:
```
{
    "current_url": "some base_url",
    "current_user": "some username",
    "current_password": "some password"
}
```
3. run:
    ```
        yarn install
    ```
4. execute to run the script:
    ```
        yarn swagger
    ```

## Example payload for the "/post/<path>" or "/post/<path>/<resource_path>" route:

```

  [{ "payload": [{
      "employeeId": 1
      },{
        "employeeId": 2
    }]
  }]

```

### Config in Sesam

#### System example :

1. Name the system ```currenttime```

2. Config :

```
{
  "_id": "currenttime",
  "type": "system:microservice",
  "docker": {
    "image": "<docker username>/currenttime:<semantic_versioning>",
    "memory": 512,
    "port": 5000,
    "current_user": "$ENV(<username for Unit4 account>)",
    "current_password": "$ENV(<password for Unit4 account>)",
    "current_url": "$ENV(<your base_url>)"
  },
  "verify_ssl": true
}
```

#### Pipe examples :

1. Name the pipe ```employees-currenttime```

2. Config :

```
{
  "_id": "employees-currenttime",
  "type": "pipe",
  "source": {
    "type": "json",
    "system": "currenttime",
    "is_since_comparable": true,
    "supports_since": true,
    "url": "/get/<path>"
  },
  "transform": {
    "type": "dtl",
    "rules": {
      "default": [
        ["copy", "*"]
      ]
    }
  },
  "pump": {
    "cron_expression": "0/10 * * * *",
    "rescan_cron_expression": "0 * * * *"
  }
}
```

1. Name the pipe ```employees-employeedetail```

2. Config :

```
{
  "_id": "employees-employeedetail",
  "type": "pipe",
  "source": {
    "type": "dataset",
    "dataset": "employees-currenttime"
  },
  "transform": {
    "type": "chained",
    "transforms": [{
      "type": "dtl",
      "rules": {
        "default": [
          ["filter",
            ["eq", "_S._deleted", false]
          ],
          ["add", "::payload",
            ["map",
              ["dict", "employeeId", "_S.EmployeeId"]
            ]
          ]
        ]
      }
    }, {
      "type": "http",
      "system": "currenttime",
      "batch_size": <an integer>,
      "url": "/post/<path>" or "post/<path>/<resource_path>"
    }]
  },
  "namespaced_identifiers": true
}
```
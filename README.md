# cogtiler ⚙️🖽 
`cogtiler` acts as a proxying tile server whixh exposes tiles from jpeg compressed Cloud Optimized GeoTIFFs using as few server resources as possible.

For tiles completely filled with image data `cogtiler` doesn't even decompress the jpeg but passes the fetched bytes untouched on to the client.

When the image dimensions are not a multiple of the tile size the client can to decide what should happen with edge tiles. `cogtiler` has three ways of handling these "out of bounds" areas: `pad`, `crop` or `mask`.

TODO: 
 - explain the three methods (image examples)
 - List endpoint types
 - Describe how to use in setups where `token` is not required

## Configuration
Cogtiler may be restricted to only proxy COGs from a fixed set of domains. This is done with a whitelist matching on prefix. The whitelist is configured
using the environment variable named `COGTILER_WHITELIST` and is an array of allowed URL prefixes encoded as a json array like:

```
COGTILER_WHITELIST=["https://api.dataforsyningen.dk/","https://septima.dk"]
```

Note: Depending on the context (where the env var is set) it may be necessary to escape the quotes.

When cogtiler recieves a request to read data from a COG at a certain url, it checks if the url starts with one of the prefixes from the whitelist. Otherwise an error is returned to the client.

## Disclaimer
`cogtiler` is built for and tested with COGs that are jpeg compressed using GDAL. It will definitely NOT work with anything else than jpeg compression. It is most likely possible to create jpeg compressed COGs that wont work with `cogtiler`.

## Development

Using vscode install the [Docker](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker) extension.

Then create

`.vscode/launch.json`:
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "cwd": "${workspaceFolder}/src/cogtiler",
            "args": [
                "main:app"
            ],
            "jinja": true
        },
        {
            "name": "Docker: Python - Fastapi",
            "type": "docker",
            "request": "launch",
            "preLaunchTask": "docker-run: debug",
            "python": {
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}/src/cogtiler",
                        "remoteRoot": "/app"
                    }
                ],
                "projectType": "fastapi"
            }
        }
    ]
}
```

and `.vscode/tasks.json`
```json
{
	"version": "2.0.0",
	"tasks": [
		{
			"type": "docker-build",
			"label": "docker-build",
			"platform": "python",
			"dockerBuild": {
				"tag": "cogtiler:latest",
				"dockerfile": "${workspaceFolder}/Dockerfile",
				"context": "${workspaceFolder}",
				"target": "debug",
				"pull": true
			}
		},
		{
			"type": "docker-run",
			"label": "docker-run: debug",
			"dependsOn": [
				"docker-build"
			],
			"dockerRun": {
				"ports": [
					{
						"containerPort": 8000,
						"hostPort": 8000
					}
				]
			},
			"python": {
				"args": [
					"main:app",
					"--host",
					"0.0.0.0",
					"--port",
					"8000"
				],
				"module": "uvicorn"
			}
		}
	]
}
```

Now you should be able to hit "Start debugging" `Docker: Python - Fastapi` which will launch `cogtiler` in a docker cointainer supporting breakpoints in your code.

`test_requests.http` has a bunch of test requests you can use to test the api. You have to install the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension to make proper use of it. 

If everything works this request `GET {{host}}/cogtiler/info?url={{cog_url}}&token={{token}}` should return something like this:

```JSON
HTTP/1.1 200 OK
date: Mon, 18 Oct 2021 11:04:50 GMT
server: uvicorn
content-length: 201
content-type: application/json
connection: close

{
  "width": 13470,
  "height": 8670,
  "compression": "image/jpeg",
  "tile_width": 1024,
  "tile_height": 1024,
  "tile_cols": 14,
  "tile_rows": 9,
  "overviews": 4
}
```
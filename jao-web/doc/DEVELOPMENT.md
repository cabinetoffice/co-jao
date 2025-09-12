NPM/NPX based tools.
===

NPM based tools are used to build and bundle resources such as CSS via SASS - this is all bundled together via Webpack


Webpack
----

Resources are bundled using webpack, somewhat based on https://saashammer.com/blog/setup-webpack-project-django/ 
but adjusted to govuk-frontend instead of bootstrap where appropriate.

This folder holds webpack config for dev and prod (webpack.dev.js and webpack.prod respectively)

AThese files configure how to chunk resources from the application and it's dependencies.





Webpack under dev:

Dev is optimised for easier debugging and faster loading of indvidual components, and can be build with:

```
$ npm run build:dev```
```

Prod is optimised for faster overall loading and can be built with:

```
$ npm run build:prod
```


from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
def hello(request):
    return {"message": "Hello World"}

@api.get("/health")
def health(request):
    return {"message": "Healthy"}

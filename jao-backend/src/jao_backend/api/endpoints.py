from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
def hello(request):
    return {"message": "Hello World"}


@api.get("/health")
def health_check(request):
    """
    Health check endpoint for load balancers and monitoring.
    """
    return {
        "status": "healthy",
        "service": "jao-backend-api",
        "version": "1.0.0"
    }

from django.shortcuts import render


def index(request):
    tasks = []
    return render(request, "home/home.html", {"tasks": tasks})

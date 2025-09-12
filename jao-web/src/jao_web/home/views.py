from django.shortcuts import render


def index(request):
    tasks = ["Optimise job advert"]
    return render(request, "home/home.html", {"tasks": tasks})

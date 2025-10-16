from django.shortcuts import render
from django.http import HttpResponse

def hello_world(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hello World</title>
        <style>
            body {
                background-color: #8B4513;
                color: white;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            h1 {
                font-size: 48px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>Hello World</h1>
    </body>
    </html>
    """
    return HttpResponse(html)

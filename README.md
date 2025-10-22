# Kirbuk

An automated SaaS product video generation service that creates narrated product videos from your application URL.

## Overview

Kirbuk is a web application that collects information about your SaaS product and automatically generates a professional product video with narration. The video generation is powered by AWS AgentCore, while this Django web application handles user input, transactions, and delivery.

## How It Works

1. **User submits product information** - Users provide their SaaS product URL, email, and optional details like test credentials and custom directions
2. **Video generation** - AWS AgentCore processes the information and creates a narrated product video
3. **Delivery** - The completed video is sent to the user's email address

## Features

- Simple, clean brown-themed interface
- Comprehensive product information collection
- Test user credentials support for secure product exploration
- Custom direction input for tailored video content
- Email delivery of finished videos

## Installation

1. Install dependencies:
```bash
cd src/kirbuk_web_app
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Start the development server:
```bash
python manage.py runserver
```

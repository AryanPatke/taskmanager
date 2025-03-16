# Task Management App

A Django-based task management application with Celery, Redis, PostgreSQL, and Docker.

## Features

- User registration and authentication (JWT).
- Task creation, update, and deletion.
- Real-time updates using WebSockets (Django Channels).
- Asynchronous email notifications (Celery).
- Fault tolerance with retry mechanisms.
- Caching using Redis.
- Dockerized for easy deployment.

## Prerequisites

- Docker
- Docker Compose

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/taskmanager.git
   cd taskmanager
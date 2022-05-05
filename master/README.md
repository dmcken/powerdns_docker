# Master Authoritative DNS Server

## Description

## Installation / Usage

1. Setup OS:
   1. Install docker
   2. Install docker-compose
   3. If ubuntu, disable systemd-resolved stub resolver (https://www.linuxuprising.com/2020/07/ubuntu-how-to-free-up-port-53-used-by.html)
2. Clone this repo to server.
3. Setup master_configuration
   ```
   cp env_server.example .env_server
   cp env_admin.example .env_admin
   ```
4. Build images:
   ```
   docker-compose build
   ```
5. Start the server:
   ```
   docker-compose up -d
   ```


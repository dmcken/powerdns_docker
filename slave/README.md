# Slave Authoritative DNS Server

## Description

## Installation / Usage

1. Setup OS:
   1. Install docker
   2. Install docker-compose
   3. If ubuntu, disable systemd-resolved stub resolver (https://www.linuxuprising.com/2020/07/ubuntu-how-to-free-up-port-53-used-by.html)
2. Clone this repo to server.
3. Switch to the slave folder within the repo
4. Setup environment:
   ```
   cp env.example .env
   ```
5. Edit .env
   1. Set 
   
6. Build images:
   ```
   docker-compose build
   ```
7. Start the server:
   ```
   docker-compose up -d
   ```


Secure password generator: https://passwordsgenerator.net/

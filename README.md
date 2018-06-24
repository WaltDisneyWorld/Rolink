<div align="center">
    <img src="https://cdn.discordapp.com/attachments/412792774581026828/453797898170269698/bloxlink.svg" height="200" width="200">
    <h2>Bloxlink</h2>
    <p align="center">
        <p>Bloxlink— a free seamless ROBLOX integration and management service for Discord.</p>
        <a href="https://blox.link">
            <b>View website »</b>
        </a>
    </p>
</div>
<p align="center">
    <a href="https://blox.link">
        <img src="https://img.shields.io/website-up-down-green-red/https/blox.link.svg?label=website">
    </a>
    <a href="https://discord.gg/g4Z2Pbx">
        <img src="https://img.shields.io/discord/372036754078826496.svg">
    </a>
</p>

### Contents
* [Packages](#packages)
* [Configuration](#configuration)
* [Basic Installation](#basic-installation)
* [License](#license)

------------------
#### Packages
Bloxlink relies on the following dependencies and frameworks:
* [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
* [discord.py](https://github.com/Rapptz/discord.py)
* [rethinkdb](https://rethinkdb.com)

------------------
#### Configuration
Bloxlink relies on a [configuration file](https://github.com/Tigerism/bloxlink/blob/master/config.py.example) in order to load the appropriate settings. You need to rename the file to ``config.py`` and put in the necessary settings. There is also a docker-compose file that must be changed.  You need to rename the file to ``docker-compose.yml``.

------------------
#### Basic Installation
Note: the application can be ran in numerous ways. Here is one way:
```
$ git clone https://github.com/Tigerism/bloxlink
$ cd bloxlink
$ docker-compose up --build
```

------------------
#### License
This repository has been released under the [Open Software License v3.0](LICENSE)

------------------
Project maintained by [justin](https://github.com/Tigerism).
Contact me on Discord: justin#1337

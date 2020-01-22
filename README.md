# Drive-Through Restaurant P2P

## Description

This repository implement a drive-through restaurant using a peer-to-peer distributed system architecture.

This restaurant simulation is composed by five different entities:

* **Restaurant:** entity responsible for managing all kitchen equipment (fryer, barbecue griller and bar).
* **Clerk:** receives the clients and records their requests.
* **Chef:** receives the requests and cooks them.
* **Waiter:** delivers the order to the respective client and receives payment.
* **Client:** makes a food request.

This entities are organized in a token-ring.

The kitchen is composed by 3 equipments:

* **Barbecue griller:** where the Chef can prepare one hamburger (average preparing time: 3 seconds)
* **Bar:** where the Chef can prepare one drink (average preparing time: 1 second)
* **Fryer:** where the Chef can prepare one package of fries (average preparing time: 5 seconds)

Each action takes a random time to be completed. This random time follows a gaussian distribution with an average time of 2 seconds and a standar deviation of 0.5 seconds. One client request is composed by at least one item (hamburger, drink or package of fries), but can be one possible combination of items with a maximum of 5 items. This request is generated randomly.

## Prerequisites

* Clone this repository

## How to run
Open two terminals:

simulation:
```console
$ python simulation.py
```
client:
```console
$ python client.py
```

## How to run (other option)
We created a run script in bash that executes 20 clients, so that is another way to execute and test the program:

```console
$ ./run.sh
```

## Git Upstream

Keep your fork sync with the upstream

```console
$ git remote add upstream git@github.com:mariolpantunes/load-balancer.git
$ git fetch upstream
$ git checkout master
$ git merge upstream/master
```

## Authors

* **Vasco Ramos:** [vascoalramos](https://github.com/vascoalramos)
* **Diogo Silva:** [HerouFenix](https://github.com/HerouFenix)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

#! /bin/bash

./hex2raw < answer2.txt > answer2hex.txt
./bufbomb -u ayekedavidr < answer2hex.txt

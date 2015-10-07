#! /bin/bash

./hex2raw < answer4.txt > answer4hex.txt
./bufbomb -u ayekedavidr -n < answer4hex.txt

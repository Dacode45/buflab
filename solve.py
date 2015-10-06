choices = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']

str = ""
for i in choices:
    for j in choices:
        str += i+j+" "
print str

import sys
from lists_rec_parser import parse

sys.stdout.write("Insert a list: ")
sys.stdout.flush()

for line in sys.stdin:
    try:
        parse(line)
        print("Parsing succeeded.")
    except Exception as e:
        print(e)
    sys.stdout.write("Insert a list: ")
    sys.stdout.flush()

print("Done")
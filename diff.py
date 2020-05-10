import difflib

def difference(old, new):
    text1 = old.splitlines()
    text2 = new.splitlines()

    with open('old.ics', 'w', newline='') as outfile:
            # Write to an ics file
            outfile.write(str(text1))

    with open('new.ics', 'w', newline='') as outfile:
            # Write to an ics file
            outfile.write(str(text2))

    iteratable = iter(difflib.unified_diff(text1, text2))
    returnData = ""
    for line in iteratable:
        if "+DTSTART" in line:
            i = 0
            temp = []
            temp.append("+BEGIN:VEVENT")
            temp.append(line)
            while i < 6:
                temp.append(next(iteratable))
                i += 1
            final = [item.replace("+","") for item in temp]
            
            for part in final:
                returnData += part + "\n"
            returnData = returnData[:-1]
            
    #print(returnData)
    return returnData

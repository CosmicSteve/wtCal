import datetime

def ics_parse(filename):
    print("ENTERING PARSE PROGRAM!")
    # Open parameter filename in read mode
    file = open(filename, 'r')
    # List of calendar events
    events = []
    # Signals when a ICS event starts
    started = False
    # Dictionary object to store ICS values in a key value pair
    current = {
        'summary': '',
        'location': '',
        'description': '',
        'start': {
            'dateTime': '',
            'timeZone': 'America/Chicago'
        },
        'end': {
            'dateTime': '',
            'timeZone': 'America/Chicago'
        }
    }

    for line in file.readlines():
        # Handle closing tag of event
        if 'END:VEVENT' in line:
            started = False
            # Append the current dictionary to the running list
            events.append(current)

        # In the middle of ICS event, add key/value to current dictionary
        if started:
            # All ICS values are colon separated
            split_pair = line.split(':')
            # [0] is key, [1] is value. [1][:-2] is used because it has '\n' at the end, so slice it off

            key = split_pair[0]
            value = split_pair[1]

            if key == 'SUMMARY':
                current['summary'] = value.replace('\\', '').replace('\n', '')
            elif key == 'LOCATION':
                current['location'] = value.replace('\n', '')
            elif key == 'DESCRIPTION':
                current['description'] = value.replace('\n', '')
            elif 'DTSTART' in key:
                value_split = value.split('T')
                value = datetime.datetime(int(value_split[0][:4]), int(value_split[0][4:6]), int(value_split[0][6:8]), int(value_split[1][:2]), int(value_split[1][2:4]), int(value_split[1][4:6]))
                value = value.isoformat()
                current['start']['dateTime'] = value.replace('\n', '')
            elif 'DTEND' in key:
                value_split = value.split('T')
                value = datetime.datetime(int(value_split[0][:4]), int(value_split[0][4:6]), int(value_split[0][6:8]), int(value_split[1][:2]), int(value_split[1][2:4]), int(value_split[1][4:6]))
                value = value.isoformat()
                current['end']['dateTime'] = value.replace('\n', '')

        # Handle opening tag of event
        if 'BEGIN:VEVENT' in line:
            started = True
            # Clear the current dictionary
            current = {
                'summary': '',
                'location': '',
                'description': '',
                'start': {
                    'dateTime': '',
                    'timeZone': 'America/Chicago'
                },
                'end': {
                    'dateTime': '',
                    'timeZone': 'America/Chicago'
                }
            }
    #print(events)
    return events
        
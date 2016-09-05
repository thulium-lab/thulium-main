
def set_loops(repeats):

    maxrepeat = 16**6
    if repeats >= maxrepeat:
        repeats = maxrepeat

    command = 0x10000000 + repeats-1

    return command

def ns_to_ticks(delay):

    tick = 12.5

    ticks = int(delay/tick)
    if ticks >= 16**6-1:
        ticks = 16**6-1
    return ticks

def jump_to_command(command):

    return command + 0x20000000

def delay(delay):

    zerodelay = 0x90000000
    if delay > 2**24-1:
        delay = 2**24-1

    return delay + zerodelay - 1

def finish():
    command  = 0xF0000000
    return command

# tests
#print delay(40)+ passed
#print ns_to_ticks(40)+ passed
#print jump_to_command(1)+ passed

# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 4
- Type C route-order/local-optimum: 13

## Stops
- T0001 node 58 customer 37: late 17.99 min, Type C route-order/local-optimum
- T0001 node 155 customer 86: late 79.33 min, Type C route-order/local-optimum
- T0003 node 55 customer 35: late 14.63 min, Type A direct-infeasible
- T0004 node 157 customer 88: late 113.65 min, Type C route-order/local-optimum
- T0039 node 9 customer 6: late 32.04 min, Type B multi-trip cascade
- T0043 node 163 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0043 node 162 customer 93: late 63.19 min, Type C route-order/local-optimum
- T0047 node 13 customer 7: late 5.93 min, Type B multi-trip cascade
- T0048 node 14 customer 7: late 5.93 min, Type B multi-trip cascade
- T0049 node 15 customer 7: late 5.93 min, Type B multi-trip cascade
- T0050 node 52 customer 32: late 47.16 min, Type C route-order/local-optimum
- T0050 node 165 customer 97: late 91.84 min, Type C route-order/local-optimum
- T0055 node 159 customer 90: late 82.18 min, Type C route-order/local-optimum
- T0078 node 158 customer 89: late 50.36 min, Type C route-order/local-optimum
- T0099 node 149 customer 80: late 51.49 min, Type C route-order/local-optimum
- T0115 node 54 customer 34: late 86.43 min, Type C route-order/local-optimum
- T0121 node 39 customer 19: late 13.66 min, Type C route-order/local-optimum
- T0121 node 166 customer 98: late 62.46 min, Type C route-order/local-optimum

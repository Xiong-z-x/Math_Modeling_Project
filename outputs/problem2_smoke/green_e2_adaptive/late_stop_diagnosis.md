# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 5
- Type C route-order/local-optimum: 12

## Stops
- T0001 node 58 customer 37: late 17.99 min, Type C route-order/local-optimum
- T0001 node 155 customer 86: late 79.33 min, Type C route-order/local-optimum
- T0003 node 55 customer 35: late 14.63 min, Type A direct-infeasible
- T0004 node 157 customer 88: late 113.65 min, Type C route-order/local-optimum
- T0023 node 23 customer 8: late 95.78 min, Type B multi-trip cascade
- T0044 node 163 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0044 node 162 customer 93: late 63.19 min, Type C route-order/local-optimum
- T0048 node 13 customer 7: late 5.93 min, Type B multi-trip cascade
- T0049 node 14 customer 7: late 5.93 min, Type B multi-trip cascade
- T0050 node 15 customer 7: late 5.93 min, Type B multi-trip cascade
- T0051 node 52 customer 32: late 47.16 min, Type C route-order/local-optimum
- T0051 node 165 customer 97: late 91.84 min, Type C route-order/local-optimum
- T0055 node 140 customer 73: late 17.98 min, Type B multi-trip cascade
- T0056 node 159 customer 90: late 82.18 min, Type C route-order/local-optimum
- T0079 node 158 customer 89: late 50.36 min, Type C route-order/local-optimum
- T0100 node 149 customer 80: late 51.49 min, Type C route-order/local-optimum
- T0122 node 39 customer 19: late 21.02 min, Type C route-order/local-optimum
- T0122 node 166 customer 98: late 69.82 min, Type C route-order/local-optimum

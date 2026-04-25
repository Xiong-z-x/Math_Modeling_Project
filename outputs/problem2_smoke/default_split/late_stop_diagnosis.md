# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 12
- Type C route-order/local-optimum: 15

## Stops
- T0001 node 40 customer 37: late 17.99 min, Type C route-order/local-optimum
- T0001 node 137 customer 86: late 79.33 min, Type C route-order/local-optimum
- T0003 node 37 customer 35: late 14.63 min, Type A direct-infeasible
- T0003 node 41 customer 38: late 119.21 min, Type C route-order/local-optimum
- T0004 node 139 customer 88: late 113.65 min, Type C route-order/local-optimum
- T0013 node 10 customer 8: late 82.73 min, Type B multi-trip cascade
- T0014 node 11 customer 8: late 95.78 min, Type B multi-trip cascade
- T0015 node 12 customer 8: late 105.04 min, Type B multi-trip cascade
- T0016 node 13 customer 8: late 119.99 min, Type B multi-trip cascade
- T0023 node 17 customer 11: late 88.35 min, Type B multi-trip cascade
- T0027 node 5 customer 6: late 61.18 min, Type B multi-trip cascade
- T0027 node 19 customer 13: late 105.32 min, Type C route-order/local-optimum
- T0028 node 6 customer 6: late 76.57 min, Type B multi-trip cascade
- T0032 node 145 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0032 node 144 customer 93: late 63.19 min, Type C route-order/local-optimum
- T0033 node 7 customer 7: late 43.90 min, Type B multi-trip cascade
- T0033 node 2 customer 3: late 26.99 min, Type B multi-trip cascade
- T0034 node 8 customer 7: late 48.62 min, Type B multi-trip cascade
- T0035 node 9 customer 7: late 72.40 min, Type B multi-trip cascade
- T0036 node 34 customer 32: late 14.91 min, Type C route-order/local-optimum
- T0036 node 147 customer 97: late 58.97 min, Type C route-order/local-optimum
- T0038 node 134 customer 83: late 1.70 min, Type C route-order/local-optimum
- T0038 node 141 customer 90: late 168.11 min, Type C route-order/local-optimum
- T0056 node 18 customer 12: late 10.00 min, Type B multi-trip cascade
- T0062 node 140 customer 89: late 43.01 min, Type C route-order/local-optimum
- T0083 node 131 customer 80: late 51.49 min, Type C route-order/local-optimum
- T0105 node 21 customer 19: late 21.02 min, Type C route-order/local-optimum
- T0105 node 148 customer 98: late 69.82 min, Type C route-order/local-optimum

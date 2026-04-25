# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 8
- Type C route-order/local-optimum: 13

## Stops
- T0001 node 45 customer 37: late 17.99 min, Type C route-order/local-optimum
- T0001 node 142 customer 86: late 79.33 min, Type C route-order/local-optimum
- T0004 node 42 customer 35: late 14.63 min, Type A direct-infeasible
- T0004 node 46 customer 38: late 119.21 min, Type C route-order/local-optimum
- T0005 node 144 customer 88: late 113.65 min, Type C route-order/local-optimum
- T0018 node 17 customer 8: late 95.78 min, Type B multi-trip cascade
- T0024 node 22 customer 11: late 78.70 min, Type B multi-trip cascade
- T0024 node 6 customer 6: late 102.33 min, Type C route-order/local-optimum
- T0029 node 7 customer 6: late 51.53 min, Type B multi-trip cascade
- T0029 node 5 customer 6: late 71.53 min, Type B multi-trip cascade
- T0033 node 150 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0033 node 149 customer 93: late 63.19 min, Type C route-order/local-optimum
- T0034 node 9 customer 7: late 18.73 min, Type B multi-trip cascade
- T0035 node 8 customer 7: late 39.14 min, Type B multi-trip cascade
- T0036 node 10 customer 7: late 43.90 min, Type B multi-trip cascade
- T0037 node 11 customer 7: late 48.62 min, Type B multi-trip cascade
- T0038 node 39 customer 32: late 14.91 min, Type C route-order/local-optimum
- T0038 node 152 customer 97: late 58.97 min, Type C route-order/local-optimum
- T0043 node 146 customer 90: late 82.18 min, Type C route-order/local-optimum
- T0064 node 145 customer 89: late 43.01 min, Type C route-order/local-optimum
- T0086 node 136 customer 80: late 51.49 min, Type C route-order/local-optimum
- T0106 node 4 customer 5: late 31.60 min, Type C route-order/local-optimum

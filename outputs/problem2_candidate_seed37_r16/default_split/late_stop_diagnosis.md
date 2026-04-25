# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 15
- Type C route-order/local-optimum: 11

## Stops
- T0001 node 40 customer 37: late 17.99 min, Type C route-order/local-optimum
- T0001 node 137 customer 86: late 79.33 min, Type C route-order/local-optimum
- T0004 node 37 customer 35: late 14.63 min, Type A direct-infeasible
- T0005 node 139 customer 88: late 113.65 min, Type C route-order/local-optimum
- T0015 node 10 customer 8: late 82.73 min, Type B multi-trip cascade
- T0016 node 11 customer 8: late 88.23 min, Type B multi-trip cascade
- T0017 node 12 customer 8: late 95.78 min, Type B multi-trip cascade
- T0018 node 13 customer 8: late 124.92 min, Type B multi-trip cascade
- T0024 node 17 customer 11: late 88.35 min, Type B multi-trip cascade
- T0029 node 5 customer 6: late 89.50 min, Type B multi-trip cascade
- T0029 node 19 customer 13: late 144.68 min, Type C route-order/local-optimum
- T0030 node 6 customer 6: late 94.23 min, Type B multi-trip cascade
- T0034 node 145 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0035 node 7 customer 7: late 72.40 min, Type B multi-trip cascade
- T0036 node 8 customer 7: late 80.98 min, Type B multi-trip cascade
- T0037 node 9 customer 7: late 92.78 min, Type B multi-trip cascade
- T0038 node 144 customer 93: late 128.51 min, Type B multi-trip cascade
- T0038 node 21 customer 19: late 12.35 min, Type C route-order/local-optimum
- T0038 node 4 customer 5: late 113.41 min, Type C route-order/local-optimum
- T0045 node 2 customer 3: late 39.00 min, Type C route-order/local-optimum
- T0061 node 18 customer 12: late 10.00 min, Type B multi-trip cascade
- T0067 node 140 customer 89: late 50.36 min, Type C route-order/local-optimum
- T0080 node 142 customer 91: late 16.80 min, Type B multi-trip cascade
- T0087 node 131 customer 80: late 51.49 min, Type C route-order/local-optimum
- T0102 node 36 customer 34: late 108.32 min, Type C route-order/local-optimum
- T0113 node 15 customer 10: late 8.20 min, Type B multi-trip cascade
- T0114 node 16 customer 10: late 26.01 min, Type B multi-trip cascade

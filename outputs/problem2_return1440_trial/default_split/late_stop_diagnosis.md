# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 12
- Type C route-order/local-optimum: 2

## Stops
- T0005 node 37 customer 35: late 14.63 min, Type A direct-infeasible
- T0019 node 10 customer 8: late 88.23 min, Type B multi-trip cascade
- T0020 node 11 customer 8: late 95.78 min, Type B multi-trip cascade
- T0021 node 12 customer 8: late 116.23 min, Type B multi-trip cascade
- T0022 node 13 customer 8: late 163.00 min, Type B multi-trip cascade
- T0028 node 17 customer 11: late 150.81 min, Type B multi-trip cascade
- T0031 node 5 customer 6: late 125.23 min, Type B multi-trip cascade
- T0032 node 6 customer 6: late 139.55 min, Type B multi-trip cascade
- T0037 node 145 customer 94: late 28.03 min, Type C route-order/local-optimum
- T0038 node 7 customer 7: late 124.72 min, Type B multi-trip cascade
- T0039 node 8 customer 7: late 112.00 min, Type B multi-trip cascade
- T0040 node 9 customer 7: late 112.00 min, Type B multi-trip cascade
- T0041 node 21 customer 19: late 12.35 min, Type C route-order/local-optimum
- T0058 node 2 customer 3: late 39.00 min, Type B multi-trip cascade
- T0063 node 18 customer 12: late 10.00 min, Type B multi-trip cascade

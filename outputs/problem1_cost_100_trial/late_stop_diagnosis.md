# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 2
- Type C route-order/local-optimum: 1

## Stops
- T0005 node 37 customer 35: late 10.18 min, Type A direct-infeasible
- T0033 node 19 customer 13: late 18.35 min, Type B multi-trip cascade
- T0079 node 4 customer 5: late 31.60 min, Type C route-order/local-optimum
- T0116 node 65 customer 50: late 17.29 min, Type B multi-trip cascade

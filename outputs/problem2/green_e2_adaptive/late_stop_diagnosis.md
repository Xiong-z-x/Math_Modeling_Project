# Late Stop Diagnosis

Type A means direct travel from depot at 08:00 is already late.
Type B means the same trip can be on time when started fresh, but physical-vehicle reuse delays it.
Type C means route order or trip composition still causes lateness even when the trip starts fresh.

## Counts
- Type A direct-infeasible: 1
- Type B multi-trip cascade: 22
- Type C route-order/local-optimum: 1

## Stops
- T0005 node 55 customer 35: late 156.10 min, Type A direct-infeasible
- T0020 node 22 customer 8: late 115.28 min, Type B multi-trip cascade
- T0020 node 10 customer 7: late 7.03 min, Type B multi-trip cascade
- T0021 node 23 customer 8: late 131.70 min, Type B multi-trip cascade
- T0021 node 11 customer 7: late 23.45 min, Type B multi-trip cascade
- T0022 node 24 customer 8: late 163.98 min, Type B multi-trip cascade
- T0022 node 12 customer 7: late 57.84 min, Type B multi-trip cascade
- T0023 node 25 customer 8: late 223.50 min, Type B multi-trip cascade
- T0023 node 13 customer 7: late 122.43 min, Type B multi-trip cascade
- T0024 node 16 customer 8: late 253.00 min, Type B multi-trip cascade
- T0027 node 20 customer 8: late 253.00 min, Type B multi-trip cascade
- T0027 node 161 customer 92: late 51.22 min, Type B multi-trip cascade
- T0028 node 74 customer 46: late 160.31 min, Type B multi-trip cascade
- T0028 node 7 customer 6: late 181.00 min, Type C route-order/local-optimum
- T0032 node 33 customer 11: late 190.00 min, Type B multi-trip cascade
- T0032 node 14 customer 7: late 159.28 min, Type B multi-trip cascade
- T0033 node 34 customer 11: late 190.00 min, Type B multi-trip cascade
- T0037 node 8 customer 6: late 181.00 min, Type B multi-trip cascade
- T0037 node 2 customer 3: late 64.67 min, Type B multi-trip cascade
- T0038 node 6 customer 6: late 181.00 min, Type B multi-trip cascade
- T0039 node 9 customer 6: late 181.00 min, Type B multi-trip cascade
- T0040 node 37 customer 13: late 174.00 min, Type B multi-trip cascade
- T0040 node 88 customer 52: late 39.46 min, Type B multi-trip cascade
- T0065 node 35 customer 12: late 10.00 min, Type B multi-trip cascade

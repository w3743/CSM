# 60-day memory decay simulation

Initial strength: 0.6; initial decay rate: 0.02.
Dots in the curve chart indicate successful uses/retrievals.

| Frequency | Uses | Day 7 | Day 14 | Day 30 | Day 45 | Day 60 | Final decay |
|---|---:|---:|---:|---:|---:|---:|---:|
| Never (0x) | 0 | 0.489 | 0.393 | 0.229 | 0.132 | 0.075 | 0.02000 |
| Once (1x) | 1 | 0.649 | 0.561 | 0.390 | 0.269 | 0.181 | 0.01486 |
| Every 30d (2x) | 2 | 0.649 | 0.561 | 0.390 | 0.490 | 0.390 | 0.00974 |
| Every 14d (5x) | 5 | 0.649 | 0.561 | 0.717 | 0.744 | 0.777 | 0.00479 |
| Weekly (9x) | 9 | 0.649 | 0.700 | 0.851 | 0.889 | 0.914 | 0.00362 |
| Every 3d (20x) | 20 | 0.846 | 0.900 | 0.953 | 0.972 | 0.981 | 0.00207 |
| Daily (60x) | 60 | 0.965 | 0.990 | 0.997 | 0.998 | 0.998 | 0.00100 |

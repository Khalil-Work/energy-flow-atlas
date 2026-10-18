# Model, accounting and ribbon geometry

## 1. Input meaning and units

Each row transfers `value` from `source` to `target`. A `FlowTable` contains
one quantity and one unit, such as power in W or mass rate in kg/s. Values
are real, finite and nonnegative; direction is encoded by the endpoints.
A `FlowRow` in kW cannot be inserted into a W table. Convert explicitly
before constructing the row. Unit names are labels, not a unit algebra or
automatic conversion system. Self-flows are rejected.

For node n, let I_n be the sum of incoming edge values and O_n the sum of
outgoing values. Its residual is R_n = I_n − O_n. Internal nodes are
declared explicitly and must satisfy

    max_internal |R_n| / max(sum_over_edges value, 1 table unit) <= tol.

The default `tol` is 1e-9. It must be finite and nonnegative. The scale
floor is one in the declared table unit. This is a floating-point
accounting tolerance, not an uncertainty interval or physical error bound.
External nodes may carry a net input or output. Missing declared nodes are
errors; they do not count as automatically balanced zero-flow nodes.
Sums use `math.fsum`; aggregate overflow is rejected explicitly.

## 2. Air-handling ledger

Assume steady state with no energy storage. Let load fraction f range from
0 to 1. The specified heat inputs are

    P_fan = 300 f W, Q_equipment = 1,200 f W, Q_envelope = 150 f W.
    Q_duct = 0.05 P_fan = 15 f W.
    Q_supply_to_room = P_fan − Q_duct = 285 f W.
    Q_room_to_return = Q_supply_to_room + Q_equipment + Q_envelope
                     = 1,635 f W.
    Q_coil = Q_room_to_return.

Thus total input 1,650 f W equals duct loss plus coil removal. No term
credits return-air energy to the fan's electrical input. Air recirculation
is a mass-flow topology; this drawing instead traces added heat/work to
its eventual removal. Supply, room and return are internal nodes.

At f=1 the seven edges sum to 5,220 W because energy is counted again at
successive transfers. That number is not an input, efficiency or heat duty.
The inputs are chosen, not obtained from measurement or an HVAC simulation.
The load-sweep GIF starts at f=0.05 because an all-zero diagram has no
meaningful automatically determined width scale. A zero-load ledger still
passes numerical balance checks.

## 3. Deterministic graph layout

The renderer runs a topological sort. All source nodes start in stage 0;
each destination's stage is one beyond its deepest parent. Alphabetical
tie breaking makes stages and placement independent of input row order.
Cycles raise a clear error before any drawing is added to an axis.

At each node the bar represents H_n = max(I_n, O_n). Nodes in a stage are
stacked with a normalized vertical gap. The automatic scale s is the
smallest of `(0.78 − gap*(node_count−1)) / sum(H_n)` across occupied
stages. This fits every stage while preserving one common height per unit.
An explicit positive `flow_scale` can be used instead if it fits every
stage. This is how the GIF keeps identical W-to-height mapping across loads.

Inlet and outlet ribbon stacks start independently at the bottom of the
bar. Balanced internal nodes exactly fill both sides; net sources/sinks
occupy the appropriate side. Edges attach to the actual left/right bar
faces. Distinct edges may cross; crossing minimization is not implemented.

## 4. Ribbon equation and the geometry regression

For 0 <= t <= 1, define p(t)=3t²−2t³ and

    x(t) = x_source + (x_target−x_source)t
    y_lower(t) = y_source + (y_target−y_source)p(t)
    y_upper(t) = y_lower(t) + value*s.

The polygon follows the lower edge forwards and the upper edge backwards
exactly once. Its vertical thickness is value*s everywhere, even for a
slanted ribbon. Its area is `(x_target−x_source)*value*s`. Following both
edges forwards would create the previous bow-tie defect, whose signed
area was zero. Regression tests intersect the actual polygon with eleven
interior vertical cuts and verify both area and constant thickness.

This is vertical thickness, not thickness normal to a curved centerline.
Zero-valued edges have zero area. Node and edge labels retain table units;
custom illustrative titles retain their disclosure.

## 5. Limits and interpretation

Conservation is necessary for a useful engineering ledger but does not
validate the physics or data provenance. An erroneous yet balanced ledger
can pass these checks. The current example assumes steady proportional
loads and does not solve heat-transfer coefficients, air temperature,
compressor work, fan performance, transients or uncertainty. The sample
allocation figure is explicitly invented demonstration data.

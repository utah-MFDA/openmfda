module thing (
	(* type="flow" *) input soln1,
	(* type="flow" *) input soln2,
	(* type="flow" *) input soln3,
	(* type="flow" *) input soln4,
	(* type="flow" *) input soln5,
	(* type="flow" *) input soln6,
	(* type="flow" *) input soln7,
	(* type="flow" *) input soln8,
	(* type="flow" *) input soln9,
	(* type="flow" *) input soln10,
	(* type="flow" *) input soln11,
	(* type="flow" *) input soln12,
	(* type="flow" *) input soln13,
	(* type="flow" *) input soln14,
	(* type="flow" *) input soln15,
	(* type="flow" *) input soln16,
	(* type="flow" *) input soln17,
	(* type="flow" *) input soln18,
	(* type="flow" *) output out1,
	(* type="flow" *) output out2,
	(* type="flow" *) output out3,
	(* type="flow" *) output out4,
	(* type="flow" *) output out5,
	(* type="flow" *) output out6,
	(* type="flow" *) output out7,
	(* type="flow" *) output out8
);

(* type="flow" *) wire	connect0, connect1, connect2, connect3, connect4, connect5, connect6, connect7, connect8, connect9, connect10, connect11, connect12, connect13, connect14, connect15, connect16, connect17, connect18, connect19, connect20, connect21, connect22, connect23, connect24, connect25, connect26, connect27, connect28, connect29, connect30, connect31, connect32, connect33;

// albumin
(* block=1, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist0	(.in_fluid(soln1), .out_fluid(connect0));
(* block=2, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist1	(.in_fluid(soln2), .out_fluid(connect1));
(* block=8, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist2	(.in_fluid(soln3), .out_fluid(connect2));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist3	(.in_fluid(soln4), .out_fluid(connect3));
diffmix_25px_0	mix0	(.a_fluid(connect0), .b_fluid(connect1), .out_fluid(connect4));
diffmix_25px_0	mix1	(.a_fluid(connect2), .b_fluid(connect4), .out_fluid(connect5));
diffmix_25px_0	mix2	(.a_fluid(connect3), .b_fluid(connect5), .out_fluid(out1));

// caffeine
(* block=5, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist6	(.in_fluid(soln1), .out_fluid(connect6));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist7	(.in_fluid(soln5), .out_fluid(connect7));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist8	(.in_fluid(soln6), .out_fluid(connect8));
diffmix_25px_0	mix3	(.a_fluid(connect6), .b_fluid(connect7), .out_fluid(connect9));
diffmix_25px_0	mix4	(.a_fluid(connect8), .b_fluid(connect9), .out_fluid(out2));

// calcium
(* block=1, major_w=14, major_h=10, minor_w=6, minor_h=5, channel_length=15 *)
p_resistor_0	resist10	(.in_fluid(soln1), .out_fluid(connect10));
(* block=8, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist11	(.in_fluid(soln7), .out_fluid(connect11));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist12	(.in_fluid(soln8), .out_fluid(connect12));
diffmix_25px_0	mix5	(.a_fluid(connect10), .b_fluid(connect11), .out_fluid(connect13));
diffmix_25px_0	mix6	(.a_fluid(connect12), .b_fluid(connect13), .out_fluid(out3));

// cocaine(*, major_w=20_ block=1_major_hminor_h=15, minor_w=11, minor_h=8, channel_length=5)
p_resistor_0	resist14	(.in_fluid(soln1), .out_fluid(connect14));
(* block=2, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist15	(.in_fluid(soln9), .out_fluid(connect15));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist16	(.in_fluid(soln10), .out_fluid(connect16));
diffmix_25px_0	mix7	(.a_fluid(connect14), .b_fluid(connect15), .out_fluid(connect17));
diffmix_25px_0	mix8	(.a_fluid(connect16), .b_fluid(connect17), .out_fluid(out4));

// ethyl
(* block=5, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist18	(.in_fluid(soln1), .out_fluid(connect18));
(* block=2, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist19	(.in_fluid(soln11), .out_fluid(connect19));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist20	(.in_fluid(soln12), .out_fluid(connect20));
diffmix_25px_0	mix9	(.a_fluid(connect18), .b_fluid(connect19), .out_fluid(connect21));
diffmix_25px_0	mix10	(.a_fluid(connect20), .b_fluid(connect21), .out_fluid(out5));

// ketone
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist22	(.in_fluid(soln1), .out_fluid(connect22));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist23	(.in_fluid(soln13), .out_fluid(connect23));
diffmix_25px_0	mix11	(.a_fluid(connect22), .b_fluid(connect23), .out_fluid(out6));

// nitrite
(* block=2, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist24	(.in_fluid(soln14), .out_fluid(connect24));
(* block=2, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist25	(.in_fluid(soln15), .out_fluid(connect25));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist26	(.in_fluid(soln1), .out_fluid(connect26));
diffmix_25px_0	mix12	(.a_fluid(connect24), .b_fluid(connect25), .out_fluid(connect27));
diffmix_25px_0	mix13	(.a_fluid(connect26), .b_fluid(connect27), .out_fluid(out7));

// salicylic
(* block=5, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist28	(.in_fluid(soln1), .out_fluid(connect28));
(* block=1, major_w=20, major_h=15, minor_w=11, minor_h=8, channel_length=5 *)
p_resistor_0	resist29	(.in_fluid(soln16), .out_fluid(connect29));
(* block=2, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist30	(.in_fluid(soln17), .out_fluid(connect30));
(* block=1, major_w=40, major_h=30, minor_w=20, minor_h=15, channel_length=5 *)
p_resistor_0	resist31	(.in_fluid(soln18), .out_fluid(connect31));
diffmix_25px_0	mix14	(.a_fluid(connect28), .b_fluid(connect29), .out_fluid(connect32));
diffmix_25px_0	mix15	(.a_fluid(connect30), .b_fluid(connect32), .out_fluid(connect33));
diffmix_25px_0	mix16	(.a_fluid(connect31), .b_fluid(connect33), .out_fluid(out8));


endmodule

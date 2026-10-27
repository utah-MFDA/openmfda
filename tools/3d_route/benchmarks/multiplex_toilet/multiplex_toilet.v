module thing(
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

// albumin
(* type="flow" *)
wire connect3, connect5, connect2, connect4, connect1, connect0;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=11, minor_h=11, minor_l=32, angle=180 *)
p_resistor_0	resist0	(.in_fluid(soln1), .out_fluid(connect0));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=19, minor_h=19, minor_l=8, angle=90 *)
p_resistor_0	resist1	(.in_fluid(soln2), .out_fluid(connect1));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=12, minor_h=12, minor_l=11, angle=90 *)
p_resistor_0	resist2	(.in_fluid(soln3), .out_fluid(connect2));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=12, minor_h=12, minor_l=28, angle=270 *)
p_resistor_0	resist3	(.in_fluid(soln4), .out_fluid(connect3));
(* angle=135 *)
diffmix_25px_0	mix0	(.a_fluid(connect1), .b_fluid(connect0), .out_fluid(connect4));
(* angle=200 *)
diffmix_25px_0	mix1	(.a_fluid(connect2), .b_fluid(connect4), .out_fluid(connect5));
(* angle=315 *)
diffmix_25px_0	mix2	(.a_fluid(connect3), .b_fluid(connect5), .out_fluid(out1));

// caffeine
(* type="flow" *)
wire connect7, connect8, connect6, connect9;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=9, minor_h=9, minor_l=12, angle=90 *)
p_resistor_0	resist6	(.in_fluid(soln1), .out_fluid(connect6));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=31, minor_h=31, minor_l=30, angle=270 *)
p_resistor_0	resist7	(.in_fluid(soln5), .out_fluid(connect7));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=25, minor_h=25, minor_l=12, angle=270 *)
p_resistor_0	resist8	(.in_fluid(soln6), .out_fluid(connect8));
(* angle=180 *)
diffmix_25px_0	mix3	(.a_fluid(connect6), .b_fluid(connect7), .out_fluid(connect9));
(* angle=180 *)
diffmix_25px_0	mix4	(.a_fluid(connect9), .b_fluid(connect8), .out_fluid(out2));

// calcium
(* type="flow" *)
wire connect11, connect12, connect10, connect13;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=0 *)
p_resistor_0	resist10	(.in_fluid(soln1), .out_fluid(connect10));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=15, minor_h=15, minor_l=8, angle=90 *)
p_resistor_0	resist11	(.in_fluid(soln7), .out_fluid(connect11));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=28, minor_h=28, minor_l=10, angle=0 *)
p_resistor_0	resist12	(.in_fluid(soln8), .out_fluid(connect12));
(* angle=90 *)
diffmix_25px_0	mix5	(.a_fluid(connect10), .b_fluid(connect11), .out_fluid(connect13));
(* angle=45 *)
diffmix_25px_0	mix6	(.a_fluid(connect12), .b_fluid(connect13), .out_fluid(out3));

// cocaine
(* type="flow" *)
wire connect17, connect16, connect14, connect15;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=90 *)
p_resistor_0	resist14	(.in_fluid(soln1), .out_fluid(connect14));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=18, minor_h=18, minor_l=15, angle=270 *)
p_resistor_0	resist15	(.in_fluid(soln9), .out_fluid(connect15));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=17, minor_h=17, minor_l=29, angle=0 *)
p_resistor_0	resist16	(.in_fluid(soln10), .out_fluid(connect16));
(* angle=180 *)
diffmix_25px_0	mix7	(.a_fluid(connect14), .b_fluid(connect15), .out_fluid(connect17));
(* angle=45 *)
diffmix_25px_0	mix8	(.a_fluid(connect16), .b_fluid(connect17), .out_fluid(out4));

// ethyl
(* type="flow" *)
wire connect21, connect19, connect18, connect20;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=10, angle=0 *)
p_resistor_0	resist18	(.in_fluid(soln1), .out_fluid(connect18));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=16, minor_h=16, minor_l=8, angle=270 *)
p_resistor_0	resist19	(.in_fluid(soln11), .out_fluid(connect19));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=21, minor_h=21, minor_l=10, angle=270 *)
p_resistor_0	resist20	(.in_fluid(soln12), .out_fluid(connect20));
(* angle=0 *)
diffmix_25px_0	mix9	(.a_fluid(connect19), .b_fluid(connect18), .out_fluid(connect21));
(* angle=90 *)
diffmix_25px_0	mix10	(.a_fluid(connect21), .b_fluid(connect20), .out_fluid(out5));

// ketone
(* type="flow" *)
wire connect23, connect22;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=0 *)
p_resistor_0	resist22	(.in_fluid(soln1), .out_fluid(connect22));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=180 *)
p_resistor_0	resist23	(.in_fluid(soln13), .out_fluid(connect23));
(* angle=110 *)
diffmix_25px_0	mix11	(.a_fluid(connect22), .b_fluid(connect23), .out_fluid(out6));

// nitrite
(* type="flow" *)
wire connect27, connect24, connect25, connect26;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=0 *)
p_resistor_0	resist24	(.in_fluid(soln14), .out_fluid(connect24));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=15, angle=90 *)
p_resistor_0	resist25	(.in_fluid(soln15), .out_fluid(connect25));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=15, angle=270 *)
p_resistor_0	resist26	(.in_fluid(soln1), .out_fluid(connect26));
(* angle=0 *)
diffmix_25px_0	mix12	(.a_fluid(connect25), .b_fluid(connect24), .out_fluid(connect27));
(* angle=315 *)
diffmix_25px_0	mix13	(.a_fluid(connect26), .b_fluid(connect27), .out_fluid(out7));

// salicylic
(* type="flow" *)
wire connect31, connect29, connect33, connect32, connect30, connect28;
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=8, minor_h=8, minor_l=8, angle=180 *)
p_resistor_0	resist28	(.in_fluid(soln1), .out_fluid(connect28));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=21, minor_h=21, minor_l=8, angle=270 *)
p_resistor_0	resist29	(.in_fluid(soln16), .out_fluid(connect29));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=18, minor_h=18, minor_l=8, angle=180 *)
p_resistor_0	resist30	(.in_fluid(soln17), .out_fluid(connect30));
(* block=3, major_w=32, major_h=32, major_l=8, minor_w=15, minor_h=15, minor_l=29, angle=270 *)
p_resistor_0	resist31	(.in_fluid(soln18), .out_fluid(connect31));
(* angle=45 *)
diffmix_25px_0	mix14	(.a_fluid(connect29), .b_fluid(connect28), .out_fluid(connect32));
(* angle=45 *)
diffmix_25px_0	mix15	(.a_fluid(connect30), .b_fluid(connect32), .out_fluid(connect33));
(* angle=0 *)
diffmix_25px_0	mix16	(.a_fluid(connect31), .b_fluid(connect33), .out_fluid(out8));
endmodule

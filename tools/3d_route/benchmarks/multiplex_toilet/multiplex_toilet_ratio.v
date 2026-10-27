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
(* part_a=2100, part_b=60, part_c=516, part_d=1290 *)
ratio4 test_albumin(soln1, soln2, soln3, soln4, out1);
(* part_a=54, part_b=1, part_c=1*)
ratio3 test_caffeine(soln1, soln5, soln6, out2);
(* part_a=225, part_b=18, part_c=2 *)
ratio3 test_calcium(soln1, soln7, soln8, out3);
(* part_a=1430, part_b=99, part_c=234 *)
ratio3 test_cocaine(soln1, soln9, soln10, out4);
(* part_a=315, part_b=6, part_c=14 *)
ratio3 test_ethyl(soln1, soln11, soln12, out5);
(* part_a=1, part_b=1 *)
ratio2 test_ketone(soln1, soln13, out6);
(* part_a=1, part_b=2, part_c=2 *)
ratio3 test_nitrite(soln14, soln15, soln1, out7);
(* part_a=50, part_b=1, part_c=2, part_d=15 *)
ratio4 test_salicylic(soln1, soln16, soln17, soln18, out8);
endmodule


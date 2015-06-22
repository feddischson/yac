
cordic_iterative_setup
input = [ -36 103 0 110 -1 248 8  ]
[ rx, ry, ra, it ] = cordic_iterative( input(1),    ... 
                                       input(2),    ...
                                       input(3),    ...
                                       input(7),        ...
                                       XY_WIDTH,    ...
                                       ANGLEWIDTH,  ...
                                       GUARDBITS,   ...
                                       RM_GAIN )

% open output file
tb_fid = fopen( TB_FILE, 'w' );

write_tb( tb_fid, 
  input( 1 ),
  input( 2 ),
  input( 3 ),
  rx,
  ry,
  ra,
  input( 7 ) );

fclose( tb_fid )

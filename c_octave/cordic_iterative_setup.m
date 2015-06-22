
%
% flags: they are also define in cordic_iterative.c and
%        cordic_iterative_pkg.vhd
C_FLAG_VEC_ROT  = 2^3;
C_FLAG_ATAN_3   = 2^2;
C_MODE_CIRC     = 0;
C_MODE_LIN      = 1;
C_MODE_HYP      = 2;

% initialize the random-generator's seed
rand('seed', 1633);


% cordic setup: 
% this must fit to the testbench
XY_WIDTH   = 8;
ANGLEWIDTH = 8;
GUARDBITS  = 2;
RM_GAIN    = 3;

TB_FILE    = './tb_data.txt'
% open test file
%tb_fid = 0;


function write_tb( fid, x_i, y_i, a_i, x_o, y_o, a_o, mode )

if fid > 0
    for x = 1 : length( x_i )
        fprintf( fid, '%ld ', fix( [ x_i(x), y_i(x), a_i(x), x_o(x), y_o(x), a_o(x), mode ] ) );
        fprintf( fid, '\n' );
    end
end

end


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%                                                                    %%%%
%%%%  File           : cordic_iterative_test.m                          %%%%
%%%%  Project        : YAC (Yet Another CORDIC Core)                    %%%%
%%%%  Creation       : Feb. 2014                                        %%%%
%%%%  Limitations    :                                                  %%%%
%%%%  Platform       : Linux, Mac, Windows                              %%%%
%%%%  Target         : Octave, Matlab                                   %%%%
%%%%                                                                    %%%%
%%%%  Author(s):     : Christian Haettich                               %%%%
%%%%  Email          : feddischson@opencores.org                        %%%%
%%%%                                                                    %%%%
%%%%                                                                    %%%%
%%%%%                                                                  %%%%%
%%%%                                                                    %%%%
%%%%  Description                                                       %%%%
%%%%        Script to test/analyze the cordic C implementation          %%%%
%%%%        and to generate stimulus data for RTL simulation.           %%%%
%%%%        This created data is used to ensure, that the C             %%%%
%%%%        implementation behaves the same than the VHDL               %%%%
%%%%        implementation.                                             %%%%
%%%%                                                                    %%%%
%%%%                                                                    %%%%
%%%%%                                                                  %%%%%
%%%%                                                                    %%%%
%%%%  TODO                                                              %%%%
%%%%        Some documentation and function description                 %%%%
%%%%                                                                    %%%%
%%%%                                                                    %%%%
%%%%                                                                    %%%%
%%%%                                                                    %%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%                                                                    %%%%
%%%%                  Copyright Notice                                  %%%%
%%%%                                                                    %%%%
%%%% This file is part of YAC - Yet Another CORDIC Core                 %%%%
%%%% Copyright (c) 2014, Author(s), All rights reserved.                %%%%
%%%%                                                                    %%%%
%%%% YAC is free software; you can redistribute it and/or               %%%%
%%%% modify it under the terms of the GNU Lesser General Public         %%%%
%%%% License as published by the Free Software Foundation; either       %%%%
%%%% version 3.0 of the License, or (at your option) any later version. %%%%
%%%%                                                                    %%%%
%%%% YAC is distributed in the hope that it will be useful,             %%%%
%%%% but WITHOUT ANY WARRANTY; without even the implied warranty of     %%%%
%%%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  %%%%
%%%% Lesser General Public License for more details.                    %%%%
%%%%                                                                    %%%%
%%%% You should have received a copy of the GNU Lesser General Public   %%%%
%%%% License along with this library. If not, download it from          %%%%
%%%% http://www.gnu.org/licenses/lgpl                                   %%%%
%%%%                                                                    %%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%



function cordic_iterative_test( )
%
%
% Please do  'mex cordic_iterative.c' to create 
% the cordic_iterative.mex
%
%
%
%


% global flags/values, they are static 
% through the whole script and defined below
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN


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
XY_WIDTH   = 25;
ANGLEWIDTH = 25;
GUARDBITS  = 2;
RM_GAIN    = 5;


% Number of tests, which are run
N_TESTS    = 10000;

% open test file
tb_fid = fopen( './tb_data.txt', 'w' );

% run test, which uses random values
run_random_test( N_TESTS, tb_fid );

% close file
fclose( tb_fid );


end



function run_random_test( N_TESTS, tb_fid )

data_a = -1 + 2 .* rand( 1, N_TESTS );
data_b = -1 + 2 .* rand( 1, N_TESTS );

% adapat data for division
data_a_div = data_a;
data_b_div = data_b;
swap_div   = ( data_b ./ data_a ) >= 2 | ( data_b ./ data_a ) < -2 ;
data_a_div( swap_div ) = data_b( swap_div );
data_b_div( swap_div ) = data_a( swap_div );

data_a_h   = ones( size( data_a ) );
data_b_h   = data_b .* 0.78;



[ ~, ~, atan_err, abs_err, it_1 ]   = ccart2pol( data_a, data_b, tb_fid );
[ ~, ~, sin_err,  cos_err, it_2 ]   = cpol2cart( data_a, data_b, tb_fid );
[ ~, div_err, it_3 ]                = cdiv( data_a_div, data_b_div, tb_fid );
[ ~, mul_err, it_4 ]                = cmul( data_a, data_b, tb_fid  );
[ ~, ~, atanh_err, sqrt_err, it_5 ] = catanh( data_a_h, data_b_h, tb_fid );
[ ~, ~, sinh_err, cosh_err, it_6 ]  = csinhcosh( data_a, tb_fid );

fprintf( ' ___________________________________________________________________\n' );
fprintf( '                  Random Value Test \n'                                 );
fprintf( ' -----+-------------------+--------------------+-------------------\n'   );
fprintf( '      |     max error     |   mean error       |  max iterations  \n'   );
fprintf( ' atan | % .14f | % .14f  | %.5f \n', max( atan_err ), mean( atan_err  ), max( it_1 ) );
fprintf( ' abs  | % .14f | % .14f  | %.5f \n', max( abs_err  ), mean( abs_err   ), max( it_1 ) );
fprintf( ' sin  | % .14f | % .14f  | %.5f \n', max( sin_err  ), mean( sin_err   ), max( it_2 ) );
fprintf( ' cos  | % .14f | % .14f  | %.5f \n', max( cos_err  ), mean( cos_err   ), max( it_2 ) );
fprintf( ' div  | % .14f | % .14f  | %.5f \n', max( div_err  ), mean( div_err   ), max( it_3 ) );
fprintf( ' mul  | % .14f | % .14f  | %.5f \n', max( mul_err  ), mean( mul_err   ), mean( it_4 ) );
fprintf( ' atanh| % .14f | % .14f  | %.5f \n', max( atanh_err), mean( atanh_err ), mean( it_5 ) );
fprintf( ' sinh | % .14f | % .14f  | %.5f \n', max( sinh_err ), mean( sinh_err  ), mean( it_6 ) );
fprintf( ' cosh | % .14f | % .14f  | %.5f \n', max( cosh_err ), mean( cosh_err  ), mean( it_6 ) );


end




function [sinh_res, cosh_res, sinh_err, cosh_err, it ]= csinhcosh( th, fid )
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

xi = repmat( (2^(XY_WIDTH-1)-1), size( th ) ); 
yi = zeros( 1, length( th ) ); 
ai = round( th .* (2^(ANGLEWIDTH-1)-1) );



mode = C_MODE_HYP;


% cordic version
[ rcosh rsinh ra, it ] = cordic_iterative( ...
                                           xi,          ... 
                                           yi,          ...
                                           ai,          ...
                                           mode,        ...
                                           XY_WIDTH,    ...
                                           ANGLEWIDTH,  ...
                                           GUARDBITS,   ...
                                           RM_GAIN );
                        
                        
                        
cosh_res = rcosh  ./ (   2^(XY_WIDTH-1)-1 );              
sinh_res = rsinh  ./ (   2^(XY_WIDTH-1)-1 );
cosh_m = cosh( th );
sinh_m = sinh( th );
sinh_err = abs(sinh_res - sinh_m );
cosh_err = abs(cosh_res - cosh_m );

      
% write TB data
write_tb( fid, xi, yi, ai, rcosh, rsinh, ra, mode );


end





function [atan_res, abs_res, atan_err, abs_err, it ]  = catanh( x, y, fid )
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

if( size( x ) ~= size( y ) )
    error( 'size error' )
end
ai = zeros( size( x ) );
xi = round( x * (2^(XY_WIDTH-1)-1) );
yi = round( y * (2^(XY_WIDTH-1)-1) );


mode = C_FLAG_VEC_ROT + C_MODE_HYP;


% cordic version
[ rx, ry, ra, it ] = cordic_iterative( xi,          ... 
                                  yi,          ...
                                  ai,          ...
                                  mode,        ...
                                  XY_WIDTH,    ...
                                  ANGLEWIDTH,  ...
                                  GUARDBITS,   ...
                                  RM_GAIN );
% matlab version                       
m_th = atanh( y ./ x );
m_r  = sqrt( x.^2 - y.^2 );

% comparison
atan_res = ra ./ 2^( (ANGLEWIDTH)-1);
abs_res  = rx ./ ( 2^(XY_WIDTH-1) -1 );
atan_err = abs( m_th - atan_res );
abs_err  = abs( m_r  -  abs_res );
      
% write TB data
write_tb( fid, xi, yi, ai, rx, ry, ra, mode );


end





function [mul_res, mul_err, it ] = cmul( x, y, fid )
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

if( size( x ) ~= size( y ) )
    error( 'size error' )
end
xi = round( x * ( 2^(XY_WIDTH-1) -1 ) );
ai = round( y * ( 2^(XY_WIDTH-1) -1 ) );
yi = zeros( size( x ) );


mode = C_MODE_LIN;

% cordic version
[ rx, rmul, ra, it ] = cordic_iterative( xi,          ... 
                                        yi,          ...
                                        ai,          ...
                                        mode,        ...
                                        XY_WIDTH,    ...
                                        ANGLEWIDTH,  ...
                                        GUARDBITS,   ...
                                        RM_GAIN );
                        
                        
mul_res  = rmul ./ (2^(ANGLEWIDTH-1)-1);
mul_err  = abs( y.*x -  mul_res );

% write TB data
write_tb( fid, xi, yi, ai, rx, rmul, ra, mode )


end





function [div_res, div_err, it ] = cdiv( x, y, fid )
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

if( size( x ) ~= size( y ) )
    error( 'size error' )
end
xi = round( x * ( 2^(XY_WIDTH-1) -1 ) );
yi = round( y * ( 2^(XY_WIDTH-1) -1 ) );
ai = zeros( size( x ) );


mode = C_FLAG_VEC_ROT + C_MODE_LIN;

% cordic version
[ rx, ry, rdiv, it ] = cordic_iterative( xi,          ... 
                                  yi,          ...
                                  ai,          ...
                                  mode,        ...
                                  XY_WIDTH,    ...
                                  ANGLEWIDTH,  ...
                                  GUARDBITS,   ...
                                  RM_GAIN );
                        
                        
div_res  = rdiv ./ (2^(ANGLEWIDTH-1)-1);
div_err  = abs( y./x -  div_res );

% write TB data
write_tb( fid, xi, yi, ai, rx, ry, rdiv, mode )

end





function [sin_res, cos_res, sin_err, cos_err, it ]= cpol2cart( th, r, fid )
global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

xi = r .* (2^(XY_WIDTH-1)-1); 
yi = zeros( 1, length( th ) ); 
ai = round( th .* (2^(ANGLEWIDTH-1)-1) );



mode = C_MODE_CIRC;


% cordic version
[ rcos rsin ra, it ] = cordic_iterative( ...
                                  xi,          ... 
                                  yi,          ...
                                  ai,          ...
                                  mode,        ...
                                  XY_WIDTH,    ...
                                  ANGLEWIDTH,  ...
                                  GUARDBITS,   ...
                                  RM_GAIN );
                        
                        
                        
cos_res = rcos  ./ (   2^(XY_WIDTH-1)-1 );              
sin_res = rsin  ./ (   2^(XY_WIDTH-1)-1 );
[ cos_m, sin_m ] = pol2cart( th, r );
sin_err = abs(sin_res - sin_m );
cos_err = abs(cos_res - cos_m );

% write TB data
write_tb( fid, xi, yi, ai, rcos, rsin, ra, mode )


end




function [atan_res, abs_res, atan_err, abs_err, it ]  = ccart2pol( x, y, fid )

global C_FLAG_VEC_ROT C_FLAG_ATAN_3 C_MODE_CIRC C_MODE_LIN C_MODE_HYP
global XY_WIDTH ANGLEWIDTH GUARDBITS RM_GAIN

if( size( x ) ~= size( y ) )
    error( 'size error' )
end
ai = zeros( size( x ) );
xi = round( x * (2^(XY_WIDTH-1)-1) );
yi = round( y * (2^(XY_WIDTH-1)-1) );


mode = C_FLAG_VEC_ROT + C_MODE_CIRC;


% cordic version
[ rx, ry, ra, it ] = cordic_iterative( xi,          ... 
                                  yi,          ...
                                  ai,          ...
                                  mode,        ...
                                  XY_WIDTH,    ...
                                  ANGLEWIDTH,  ...
                                  GUARDBITS,   ...
                                  RM_GAIN );
% matlab version                       
[m_th, m_r ] = cart2pol( x, y );

% comparison
atan_res = ra ./ 2^( (ANGLEWIDTH)-1);
abs_res  = rx ./ ( 2^(XY_WIDTH-1) -1 );
atan_err = abs( m_th - atan_res );
abs_err  = abs( m_r  -  abs_res );

% write TB data
write_tb( fid, xi, yi, ai, rx, ry, ra, mode )

end





function write_tb( fid, x_i, y_i, a_i, x_o, y_o, a_o, mode )

if fid > 0
    for x = 1 : length( x_i )
        fprintf( fid, '%ld ', fix( [ x_i(x), y_i(x), a_i(x), x_o(x), y_o(x), a_o(x), mode ] ) );
        fprintf( fid, '\n' );
    end
end

end

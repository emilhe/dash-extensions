import React from 'react';
import { ImgComparisonSlider } from '@img-comparison-slider/react';
import { Props } from '../components/BeforeAfter'; // reuse the interface

const BeforeAfter = ({
  id,
  before,
  after,
  width = '100%',
  height = 'auto',
  hover = true,
  value = 50,
  direction = 'horizontal',
  keyboard = 'enabled',
}: Props) => (
  <div id={id}>
    <ImgComparisonSlider
      hover={hover}
      value={value}
      direction={direction}
      keyboard={keyboard}
    >
      <img slot="first" width={width} height={height} {...before} />
      <img slot="second" width={width} height={height} {...after} />
    </ImgComparisonSlider>
  </div>
);

export default BeforeAfter;

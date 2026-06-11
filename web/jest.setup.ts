import '@testing-library/jest-dom';
import { mutate } from 'swr';

beforeEach(() => {
  mutate(() => true, undefined, { revalidate: false });
});

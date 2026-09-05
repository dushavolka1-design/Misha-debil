import type { Meta, StoryObj } from '@storybook/react';

import { FileDropzone } from '../FileDropzone';

const meta: Meta = {
  title: 'DAR/UploadZone',
};
export default meta;

export const Idle: StoryObj = {
  render: () => <FileDropzone />,
};

export const Drag: StoryObj = {
  render: () => <FileDropzone status="drag" />,
};

export const Selected: StoryObj = {
  render: () => <FileDropzone status="selected" fileName="contract.pdf" />,
};

export const Scanning: StoryObj = {
  render: () => <FileDropzone status="scanning" fileName="contract.pdf" />,
};

export const Error: StoryObj = {
  render: () => <FileDropzone status="error" errorText="Файл слишком большой" />,
};

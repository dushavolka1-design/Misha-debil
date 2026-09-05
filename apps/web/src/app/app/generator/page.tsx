import GeneratorHubClient from './GeneratorHubClient';
import { SectionErrorBoundary } from '../../../components/SectionErrorBoundary';

export default function GeneratorPage() {
  return (
    <SectionErrorBoundary sectionLabel="Генерация">
      <GeneratorHubClient />
    </SectionErrorBoundary>
  );
}

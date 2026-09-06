import AnalyzerHubClient from './AnalyzerHubClient';
import { SectionErrorBoundary } from '../../../components/SectionErrorBoundary';

export default function AnalyzerPage() {
  return (
    <SectionErrorBoundary sectionLabel="Анализатор">
      <AnalyzerHubClient />
    </SectionErrorBoundary>
  );
}

import { AppLayout } from "../../modules/layout/components/AppLayout";
import { PageContainer } from "../../modules/shared/components/PageContainer";
import { SectionHeader } from "../../modules/layout/components/SectionHeader";

export const Settings = () => {
  return (
    <AppLayout>
      <PageContainer>
        <SectionHeader title="Settings" description="Manage your preferences" />
        <div className="flex-1 flex items-center justify-center text-slate-400">Settings coming soon</div>
      </PageContainer>
    </AppLayout>
  );
};

import { AppLayout } from "../../modules/layout/components/AppLayout";
import { PageContainer } from "../../modules/shared/components/PageContainer";
import { SectionHeader } from "../../modules/layout/components/SectionHeader";

export const Profile = () => {
  return (
    <AppLayout>
      <PageContainer>
        <SectionHeader title="Profile" description="Manage your personal information" />
        <div className="flex-1 flex items-center justify-center text-slate-400">Profile coming soon</div>
      </PageContainer>
    </AppLayout>
  );
};

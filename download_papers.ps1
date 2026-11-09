$ErrorActionPreference = 'Stop'
$root = Join-Path $PSScriptRoot 'papers'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$papers = @(
    @('01_HaWoR_CVPR2025.pdf','https://arxiv.org/pdf/2501.02973'),
    @('02_BIGS_CVPR2025.pdf','https://openaccess.thecvf.com/content/CVPR2025/papers/On_BIGS_Bimanual_Category-agnostic_Interaction_Reconstruction_from_Monocular_Videos_via_3D_CVPR_2025_paper.pdf'),
    @('03_HOT3D_CVPR2025.pdf','https://openaccess.thecvf.com/content/CVPR2025/papers/Banerjee_HOT3D_Hand_and_Object_Tracking_in_3D_from_Egocentric_Multi-View_CVPR_2025_paper.pdf'),
    @('04_OAKINK2_CVPR2024.pdf','https://openaccess.thecvf.com/content/CVPR2024/papers/Zhan_OAKINK2_A_Dataset_of_Bimanual_Hands-Object_Manipulation_in_Complex_Task_CVPR_2024_paper.pdf'),
    @('05_2HandedAfforder_ICCV2025.pdf','https://openaccess.thecvf.com/content/ICCV2025/papers/Heidinger_2HandedAfforder_Learning_Precise_Actionable_Bimanual_Affordances_from_Human_Videos_ICCV_2025_paper.pdf'),
    @('06_DexMV_ECCV2022.pdf','https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136990562.pdf'),
    @('07_Learning_Transfer_Hand_Skills_ICRA2025.pdf','https://arxiv.org/pdf/2501.04169'),
    @('08_Cross_Embodiment_Dexterous_Grasping_ICLR2025.pdf','https://proceedings.iclr.cc/paper_files/paper/2025/file/ca8c6f28d8ba1e732e3f217ab05c4ec0-Paper-Conference.pdf'),
    @('09_ManipTrans_CVPR2025.pdf','https://openaccess.thecvf.com/content/CVPR2025/papers/Li_ManipTrans_Efficient_Dexterous_Bimanual_Manipulation_Transfer_via_Residual_Learning_CVPR_2025_paper.pdf'),
    @('10_DexTrack_ICLR2025.pdf','https://proceedings.iclr.cc/paper_files/paper/2025/file/d5a1f97d2b922da92e880d13b7d2bf02-Paper-Conference.pdf'),
    @('11_Dexplore_CoRL2025.pdf','https://raw.githubusercontent.com/mlresearch/v305/main/assets/xu25d/xu25d.pdf'),
    @('12_DexMimicGen_ICRA2025.pdf','https://arxiv.org/pdf/2410.24185'),
    @('13_CyberDemo_CVPR2024.pdf','https://openaccess.thecvf.com/content/CVPR2024/papers/Wang_CyberDemo_Augmenting_Simulated_Human_Demonstration_for_Real-World_Dexterous_Manipulation_CVPR_2024_paper.pdf'),
    @('14_DexUMI_CoRL2025.pdf','https://raw.githubusercontent.com/mlresearch/v305/main/assets/xu25b/xu25b.pdf'),
    @('15_Human2Sim2Robot_CoRL2025.pdf','https://raw.githubusercontent.com/mlresearch/v305/main/assets/lum25a/lum25a.pdf'),
    @('16_RoboTwin_CVPR2025.pdf','https://openaccess.thecvf.com/content/CVPR2025/papers/Mu_RoboTwin_Dual-Arm_Robot_Benchmark_with_Generative_Digital_Twins_CVPR_2025_paper.pdf'),
    @('17_ViViDex_ICRA2025.pdf','https://arxiv.org/pdf/2404.15709'),
    @('18_WHOLE_CVPRFindings2026.pdf','https://openaccess.thecvf.com/content/CVPR2026F/papers/Ye_WHOLE_World-Grounded_Hand-Object_Lifted_from_Egocentric_Videos_CVPRF_2026_paper.pdf'),
    @('19_UniDex_CVPR2026.pdf','https://openaccess.thecvf.com/content/CVPR2026/papers/Zhang_UniDex_A_Robot_Foundation_Suite_for_Universal_Dexterous_Hand_Control_CVPR_2026_paper.pdf')
)
$results = foreach ($entry in $papers) {
    $path = Join-Path $root $entry[0]
    try {
        if (-not (Test-Path -LiteralPath $path)) {
            Invoke-WebRequest -Uri $entry[1] -OutFile $path -TimeoutSec 90 -MaximumRetryCount 2
        }
        $bytes = [IO.File]::ReadAllBytes($path)
        if ($bytes.Length -lt 10000 -or [Text.Encoding]::ASCII.GetString($bytes,0,4) -ne '%PDF') { throw 'Not a valid PDF' }
        [pscustomobject]@{file=$entry[0];url=$entry[1];bytes=$bytes.Length;status='ok'}
    } catch {
        Remove-Item -LiteralPath $path -ErrorAction SilentlyContinue
        [pscustomobject]@{file=$entry[0];url=$entry[1];bytes=0;status=$_.Exception.Message}
    }
}
$results | Export-Csv -LiteralPath (Join-Path $PSScriptRoot 'download_manifest.csv') -NoTypeInformation -Encoding UTF8
$results | Format-Table -AutoSize

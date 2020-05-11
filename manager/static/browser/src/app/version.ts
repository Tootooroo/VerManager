export interface Version {
    vsn: string;
    sn: string;
}

export interface BuildInfo {
    [key: string]: string;
}

export interface VersionBuild {
    ver: Version;
    info: BuildInfo;
}

export interface Version {
    vsn: string;
    rev: string;
}

export interface BuildInfo {
    [key: string]: string;
}

export interface VersionBuild {
    ver: Version;
    info: BuildInfo;
}

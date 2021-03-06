import { join } from "path";
import { existsSync } from "fs";
import { ExtensionContext, ProgressLocation, window, workspace } from "vscode";
import { IS_WIN, LS_VENV_NAME, GALAXY_LS, GALAXY_LS_PACKAGE, PYTHON_UNIX, PYTHON_WIN } from "./constants";
import { execAsync } from "./utils";

export async function installLanguageServer(context: ExtensionContext): Promise<string> {
    // Check if the LS is already installed
    let venvPath = getVirtualEnvironmentPath(context.extensionPath, LS_VENV_NAME)
    let venvPython = getPythonFromVenvPath(venvPath);
    const isInstalled = await isPythonModuleInstalled(venvPython, GALAXY_LS);
    if (isInstalled) {
        return Promise.resolve(venvPython);
    }

    // Install with progress bar
    return window.withProgress({
        location: ProgressLocation.Notification,
    }, (progress): Promise<string> => {
        return new Promise<string>(async (resolve, reject) => {
            try {
                progress.report({ message: "Installing Galaxy language server..." });

                // Get python interpreter
                const python = await getPython();

                // Create virtual environment
                venvPath = await createVirtualEnvironment(python, LS_VENV_NAME, context.extensionPath);

                // Install language server package
                venvPython = getPythonFromVenvPath(venvPath);
                const isInstalled = await intallPythonPackage(venvPython, GALAXY_LS_PACKAGE)
                if (!isInstalled) {
                    const errorMessage = "There was a problem trying to install the Galaxy language server.";
                    window.showErrorMessage(errorMessage);
                    throw new Error(errorMessage);
                }

                window.showInformationMessage("Galaxy Tools extension is ready!");
                resolve(venvPython);
            } catch (err) {
                window.showErrorMessage(err);
                console.error(`[gls] installLSWithProgress err: ${err}`);
                reject(err);
            }
        });
    });
}

function getPythonFromVenvPath(venvPath: string): string {
    return IS_WIN ? join(venvPath, "Scripts", PYTHON_WIN) : join(venvPath, "bin", PYTHON_UNIX);
}

function getPythonCrossPlatform(): string {
    return IS_WIN ? PYTHON_WIN : PYTHON_UNIX;
}

function getVirtualEnvironmentPath(extensionDirectory: string, envName: string): string {
    const path = join(extensionDirectory, envName);
    return path;
}

async function isPythonModuleInstalled(python: string, moduleName: string): Promise<boolean> {
    if (!existsSync(python)) {
        console.log(`[gls] Python not found in: ${python}`);
        return false;
    }
    let checkPythonModuleInstalledCmd = `"${python}" -c "import sys, pkgutil; print('installed' if pkgutil.find_loader('${moduleName}') else 'not found')"`;
    try {
        const result = await execAsync(checkPythonModuleInstalledCmd);
        return result === "installed";
    } catch (err) {
        console.error(`[gls] isPythonModuleInstalled err: ${err}`);
        return false;
    }
}

async function intallPythonPackage(python: string, packageName: string): Promise<boolean> {
    const installPipPackageCmd = `"${python}" -m pip install ${packageName}`;
    try {
        await execAsync(installPipPackageCmd);
        return true
    } catch (err) {
        console.error(`[gls] intallPythonPackage err: ${err}`);
        return false;
    }
}

async function getPythonVersion(python: string): Promise<number[]> {
    const getPythonVersionCmd = `"${python}" --version`;
    const version = await execAsync(getPythonVersionCmd);
    const numbers = version.match(new RegExp(/\d/g));
    if (numbers === null) return [0, 0];
    return numbers.map(v => Number.parseInt(v));
}

async function checkPythonVersion(python: string): Promise<boolean> {
    try {
        const [major, minor] = await getPythonVersion(python);
        return major === 3 && minor >= 8;
    } catch {
        return false;
    }
}

async function getPython(): Promise<string> {
    let python = workspace.getConfiguration("python").get<string>("pythonPath", getPythonCrossPlatform());
    if (await checkPythonVersion(python)) {
        return python;
    }

    let result = await window.showInputBox({
        ignoreFocusOut: true,
        placeHolder: "Enter a path to the python 3.8+.",
        prompt: "This python will be used to create a virtual environment inside the extension directory.",
        validateInput: async (value: string) => {
            if (await checkPythonVersion(value)) {
                return null;
            } else {
                return "Not a valid python path!";
            }
        },
    });

    // User canceled the input
    if (result === "undefined") {
        throw new Error("Python 3.8+ is required!");
    }

    return result as string;
}

async function createVirtualEnvironment(python: string, name: string, cwd: string): Promise<string> {
    const path = getVirtualEnvironmentPath(cwd, name);
    if (!existsSync(path)) {
        const createVenvCmd = `"${python}" -m venv ${name}`;
        await execAsync(createVenvCmd, { cwd });
    }
    return path;
}

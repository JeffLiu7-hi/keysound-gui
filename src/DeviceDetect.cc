#include "Audio.hpp"
#include "DeviceDetect.hpp"
#include "KeyDetect.hpp"
#include "utils.hpp"
#include <cstring>
#include <iostream>
#include <string>
#include <utility>
#include <thread>
#include <vector>
#include <map>

extern "C" {
#include <linux/netlink.h>
#include <sys/socket.h>
#include <sys/msg.h>
#include <unistd.h>
}

/*代码注释 / Code Comments*/
/*CN 中文               English*/
/*Note: Translated using an online tool and some elbow grease,
 *so the translation may not be 100% accurate.
 */



#define UEVENT_BUFFER_SIZE 512

// static const std::string cmd1 = "grep -E 'Handlers|EV=' /proc/bus/input/devices | grep -B1 'EV=1[2]001[3Ff]' | grep -Eo 'event[0-9]+'";
static const std::string cmd1 = "grep -E 'Handlers|EV=' /proc/bus/input/devices | grep -B1 'EV=1[2]001' | grep -Eo 'event[0-9]+'";
static const std::string cmd2 = "grep -B2 'EV=1[2]001[3Ff]' /proc/bus/input/devices | grep event";

// 是否监控设备		Whether to monitor the hardware
static bool detect = true;

// 所有键盘监控线程	All keyboard monitoring threads
static std::vector<std::thread> all_threads;

// 停止监控前应该先停止所有的键盘监控线程		All keyboard monitoring threads should be stopped before stopping monitoring
void stop_detect() {
    detect = false;
}

// 判断是不是键盘设备，输入是number		Determine if it is a keyboard device, input is "number"
static bool is_keyboard(std::string &event_id) {
    if (event_id.empty()) return false;

    FILE *pip = popen((cmd2 + event_id).c_str(), "r");

    if (!pip) {
        std::cout << "error occured" << std::endl;
        return false;
    }

    char buf[8];
    char *tmp = fgets(buf, 8, pip);

    pclose(pip);

    if (tmp) return true;
    else return false;
}

// 初始化netlink，获得socket		Initialize netlink, get socket
static int init_socket() {
    int sock_fd;
    struct sockaddr_nl sa;

    sock_fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_KOBJECT_UEVENT);
    if (sock_fd < 0) {
        std::cout << "init socket error" << std::endl;
        return -1;
    }

    std::memset(&sa, 0, sizeof(struct sockaddr_nl));
    sa.nl_family = AF_NETLINK;
    sa.nl_pid = getpid();
    sa.nl_groups = 1;

    int i = bind(sock_fd, (struct sockaddr *)&sa, sizeof(struct sockaddr_nl));
    if (i < 0) {
        std::cout << "init socket bind error occured" << std::endl;
        close(sock_fd);
        return -1;
    }

    return sock_fd;
}

// 获取字符串中的event id		Get the event id as a string
static std::string get_event_id(std::string buf) {
    auto pos = buf.find("event");

    // 未找到event	if the event was not found
    if (pos == std::string::npos) return "";

    auto pos_stop = buf.find("/", pos);
    if (pos_stop == std::string::npos) pos_stop = buf.size();

    auto event_id = buf.substr(pos+5, pos_stop-pos-1);

    return event_id;
}

// 是否是新插入1，拔出-1，其他0		returns 1 if device newly inserted, -1 if unplugged, otherwise return 0
static int device_state(std::string str) {
    if (str.find("add") == 0) return 1;
    else if (str.find("remove") == 0) return -1;
    else return 0;
}

static void start_exists_device(Audio *audio, Mixer *mixer) {
    // 执行命令，获得键盘设备文件	Execute the command to get the keyboard device file
    FILE *pip = popen(cmd1.c_str(), "r");

    if (!pip) {
        std::cout << "error occured" << std::endl;
    }

    char buf[64];
    while (!feof(pip)) {
        std::memset(buf, '\0', 64);
        if (fgets(buf, 64, pip) != NULL) {
            // 创建键盘监控线程		Create keyboard monitoring thread
            std::string str_event_id = get_event_id(buf);
            str_event_id.erase(str_event_id.size() - 1);
            all_threads.push_back(std::thread(key_detect, str_event_id, audio, mixer));
        }
    }

    pclose(pip);
}

// 键盘监控	Keyboard monitoring
void device_detect(Audio *audio, Mixer *mixer) {
    // 首先启动已有的设备	Start the existing equipment first
    start_exists_device(audio, mixer);
    fd_set fds;
    struct timeval tv;

    int sock_fd = init_socket();
    if (sock_fd < 0) {
        std::cout << "init error" << std::endl;
        return;
    }

    char buf[UEVENT_BUFFER_SIZE];

    // while的条件要更改，本身监控是一个线程，所以要安全退出
    // The condition of while needs to be changed, the monitoring itself is a thread,
    // so it is necessary to exit safely
    while (detect) {
        FD_ZERO(&fds);
        FD_SET(sock_fd, &fds);
        tv.tv_sec = 0;
        tv.tv_usec = 100 * 1000;

        int ret = select(sock_fd + 1, &fds, NULL, NULL, &tv);
        if (ret < 0) continue;
        if (!(ret > 0 && FD_ISSET(sock_fd, &fds))) continue;

        std::memset(buf, '\0', UEVENT_BUFFER_SIZE);
        if (recv(sock_fd, buf, UEVENT_BUFFER_SIZE, 0) > 0) {
            std::string str_event_id = get_event_id(buf);
            // int int_event_id = atoi(str_event_id.c_str());

            // 判断状态，增加设备还是删除设备
	    // Determine the status, add or delete equipment
            int state = device_state(buf);
            switch (state) {
                case 1:
                {
                    // 若是增加设备		If you add equipment
                    // 判断设备线程是否已经存在 Determine whether the device thread already exists
                    if (event_id_exists(str_event_id)) break;
                    else {
                        // 判断是不是键盘设备	Determine if it is a keyboard device
                        if (is_keyboard(str_event_id)) {
                            // 新建线程		Create new thread
                            all_threads.push_back(std::thread(key_detect, str_event_id, audio, mixer));
                        }
                    }
                    break;
                }
                case -1:
                {
                    // 删除					Delete
                    // 判断是否已经存在于key_detect_threads中	Determine whether it already exists in key_detect_threads
                    if (event_id_exists(str_event_id)) {
                        del_event_id(str_event_id);
                    }
                    break;
                }
                default:
                    break;

            }
        }
    }

    clear_all_key_detect_threads();
    if (sock_fd > 0) close(sock_fd);

    // 等待子线程结束	Wait for the child thread
    for (auto &th: all_threads) {
        th.join();
    }
}

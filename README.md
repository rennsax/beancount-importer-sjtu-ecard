# SJTU 校园卡账单导入 Beancount

该项目用于将校园卡流水账单转换为 [Beancount](https://beancount.github.io/) 格式的 transaction。

## 安装

项目暂未发布到 PyPI，只能通过源码安装：

``` shell
git clone https://github.com/rennsax/beancount_sjtu_ecard_importer.git
cd beancount_sjtu_ecard_importer
pip3 install -e .
bean-extract-sjtu-ecard --help
```

## 使用方式

登入[我的校园卡](https://weixin.sjtu.edu.cn/xxzx/sjtu-net/ecard/ecard.php)，进入“流水查询”，选择起始终止日期后点击“查询流水”。

按 F12 打开控制台，进入 console 选项栏，执行以下代码：

``` javascript
(function() {
    'use strict';
    const element = document.querySelector('.table');
    const content = element.outerHTML;

    const blob = new Blob([content], { type: 'text/html' });

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'sjtu-meal-card.html';

    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
})();
```

执行后浏览器会自动下载文件 `sjtu-meal-card.html`，是 HTML 格式的流水信息。

``` shell
# 提取 transaction 并输出到标准输出
bean-extract-sjtu-ecard sjtu-meal-card.html

# 输出到文件
bean-extract-sjtu-ecard sjtu-meal-card.html -o sjtu-ecard.bean
```

## 可能遇到的问题

因为我只有自己的账单作为测试数据，没有办法保证完备性，所以对于部分消费点，程序不知道怎么将其映射为 Expenses 账户，会抛出异常 `Unknown payee: ...`。可以参考下面的开发说明直接更改源码。

## 开发说明

`beancount_importer_sjtu_ecard.py` 中 `payee_to_account` 函数定义了如何从消费地点 (payee) 映射到对应的 Expenses 账户。默认的实现对于本人来说够用，如果需要自定义 Expenses 账户的名字或者补充没有考虑到的消费地点，可以自行替换这部分的实现。
